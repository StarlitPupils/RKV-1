"""Existing-output diagnostic only; no model calls or retrieval implementation."""
def classify(gold_papers,selected_papers,correct,grounded):
 gold=set(gold_papers);selected=set(selected_papers)
 if type(correct) is not bool or grounded is not None and type(grounded) is not bool:raise ValueError('Invalid verdict flags')
 if not gold:
  if grounded is not None:raise ValueError('Unannotated quality must remain null')
  return 'unannotated_proxy'
 present=bool(gold&selected)
 if grounded and (not present or not correct):raise ValueError('Grounded flag contradicts source or verdict')
 if not present:return 'no_annotated_paper_available'
 if not correct:return 'annotated_paper_available_verdict_wrong'
 if not grounded:return 'verdict_correct_rationale_incomplete'
 return 'grounded_correct'

def summarize(rows):
 counts={k:0 for k in ('unannotated_proxy','no_annotated_paper_available','annotated_paper_available_verdict_wrong','verdict_correct_rationale_incomplete','grounded_correct')}
 for row in rows:counts[row]+=1
 failures=sum(counts[k] for k in ('no_annotated_paper_available','annotated_paper_available_verdict_wrong','verdict_correct_rationale_incomplete'))
 return {'counts':counts,'all_rows':len(rows),'annotated_grounded_failures':failures,'missing_paper_strict_majority':None if not failures else 2*counts['no_annotated_paper_available']>failures}
