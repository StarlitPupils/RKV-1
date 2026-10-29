"""Annotation-aware diagnostic control only, never deployable retrieval."""
def oracle_papers(locators,gold_ids,cap=4096,count=12):
 if type(cap)is not int or cap<0 or type(count)is not int or count<0:raise ValueError('Invalid budget')
 targets=sorted(set(map(str,gold_ids)));selected=[];used=0;rejected=[]
 for key in targets:
  if key not in locators:raise ValueError('Unknown original annotated paper')
  n=locators[key]['length']
  if type(n)is not int or n<=0:raise ValueError('Invalid original row length')
  if len(selected)>=count:rejected.append({'paper_id':key,'reason':'count_stop'})
  elif n>cap-used:rejected.append({'paper_id':key,'reason':'remaining_byte_budget'})
  else:selected.append(key);used+=n
 return {'selected_ids':selected,'original_record_B':used,'rejections':rejected,'annotation_aware_not_deployable':True}
