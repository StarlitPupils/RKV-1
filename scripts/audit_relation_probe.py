"""Independent dense lexical feature/logit and explicit-label denominator audit."""
from collections import Counter
import hashlib,math,re
N=389

def reference_features(claim,document,claim_only=False):
    ct=Counter(re.findall(r'[a-z0-9]+',claim.casefold()));dt=Counter() if claim_only else Counter(re.findall(r'[a-z0-9]+',document.casefold()));dense=[0.]*N
    counts=(ct,dt,{word:min(ct[word],dt[word]) for word in ct if word in dt})
    for channel,values in enumerate(counts):
        bins=[0. for _ in range(128)]
        for term in sorted(values):
            raw=hashlib.sha256(term.encode('utf-8')).digest();index=sum(raw[i]<<(8*i) for i in range(8))%128;bins[index]+=1+math.log(values[term])
        norm=math.sqrt(sum(value*value for value in bins))
        for j,value in enumerate(bins):dense[128*channel+j]=value/norm if norm else 0.
    neg=('no','not','never','without','neither','nor');cneg=any(word in ct for word in neg);dneg=any(word in dt for word in neg)
    dense[384]=1. if cneg else 0.;dense[385]=1. if dneg and not claim_only else 0.;dense[386]=1. if cneg!=dneg and not claim_only else 0.;dense[387]=sum(word in dt for word in ct)/len(ct) if ct and not claim_only else 0.;dense[388]=1.;return dense

def reference_predict(model,claim,document):
    if model['method']=='majority':score=model['training_class_counts']['SUPPORT']/model['training_pairs']
    else:
        vector=reference_features(claim,document,model['method']=='claim_only');z=sum(vector[i]*model['weights'][i] for i in range(N));bounded=min(40.,max(-40.,z));score=1./(1.+math.exp(-bounded))
    return {'predicted_relation':'SUPPORT' if score>=.5 else 'CONTRADICT','support_score_uncalibrated':score,'scientific_entailment_verified':False,'generated_answer':None}

def relation_metrics(gold,predictions):
    labels=('CONTRADICT','SUPPORT')
    if any(value not in (*labels,None) for value in gold.values()) or any(value not in labels for value in predictions.values()):raise ValueError('Only explicit annotated binary labels accepted; unknown is not NEI')
    explicit={key:value for key,value in gold.items() if value is not None};covered=set(explicit)&set(predictions);confusion={label:{predicted:0 for predicted in labels} for label in labels}
    for key in covered:confusion[explicit[key]][predictions[key]]+=1
    totals={label:sum(v==label for v in explicit.values()) for label in labels};retrieved={label:sum(confusion[label].values()) for label in labels};correct={label:confusion[label][label] for label in labels};allcorrect=sum(correct.values());balanced=sum(correct[label]/retrieved[label] for label in labels)/2 if all(retrieved.values()) else None
    return {'all_selected_pairs':len(predictions),'all_explicit_labeled_gold_pairs':len(explicit),'retrieved_explicit_gold_pairs':len(covered),'missing_explicit_gold_pairs':len(explicit)-len(covered),'ambiguous_gold_pairs':sum(v is None for v in gold.values()),'selected_ambiguous_gold_pairs':sum(key in predictions and value is None for key,value in gold.items()),'selected_without_gold_annotation':len(set(predictions)-set(gold)),'class_total_gold':totals,'class_retrieved_gold':retrieved,'class_correct':correct,'confusion_on_retrieved_gold':confusion,'correct_retrieved_gold':allcorrect,'conditional_accuracy_on_retrieved_labeled_gold':allcorrect/len(covered) if covered else None,'all_labeled_gold_correct_coverage':allcorrect/len(explicit) if explicit else None,'balanced_accuracy_on_retrieved_labeled_gold':balanced,'unannotated_are_not_NEI_or_negative':True}
