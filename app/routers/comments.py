# def create_nlp_row_dict(user_answers: Dict[int, List[str]], correct_answers: Dict[int, List[str]],assessment_id: str,student_id: str) -> Dict:

#     for question_id, correct_answer in correct_answers.items():
#         user_answer = user_answers.get(question_id, [])
#         for answer in correct_answer:
#             for stu_answer in user_answer:
#                 row = {"assessment_id":assessment_id,"question_id":question_id,
#                        "student_id":student_id, "ref_answer":answer, "stu_answer":stu_answer}

#     return row

# def mark_multiple_nlp(df, assessment_id):
#     nlp_df:pd.DataFrame = pd.DataFrame(columns = ['assessment_id','question_id', 'student_id', 'ref_answer', 'stu_answer', 'num_answer', 'mark'])
#     questions = df["question_id"].unique().tolist()
#     users = df["student_id"].unique().tolist()
#     for question in questions:
#         correct_answers = df[df['question_id'] == question]["ref_answer"].unique().tolist()
#         num_answer = int(df[df['question_id'] == question]['num_answer'].iloc[0])
#         mark = df[df['question_id'] == question]['mark'].iloc[0]
#         correct_answers_dict = {question:correct_answers}
#         for user in users:
#             user_answers = df[(df['question_id'] == question)& (df["student_id"] == user)]['stu_answer'].unique().tolist()
#             user_answers_dict = {question:user_answers}
#             #row = create_nlp_row_dict(user_answers_dict,correct_answers_dict, assessment_id, user)
#             for question_id, correct_answer in correct_answers_dict.items():
#                 user_answer = user_answers_dict.get(question_id, [])
#                 for answer in correct_answer:
#                     for stu_answer in user_answer:
#                         row = {"assessment_id":assessment_id,"question_id":question_id,
#                             "student_id":user,"num_answer":num_answer, "ref_answer":answer,
#                               "stu_answer":stu_answer, "num_answer":num_answer, "mark":mark}
#                         nlp_df = nlp_df.append(row, ignore_index = True)
#     # nlp_df["assessment_id"].fillna(assessment_id, inplace=True)
#     nlp_df['preds'] = predict.predict(nlp_df,  'ref_answer', 'stu_answer')/2
#     print(predict.predict(nlp_df,  'ref_answer', 'stu_answer')/2)
#     score_df = process_multi_nlp(nlp_df, assessment_id=assessment_id)
#     return score_df

# def process_multi_nlp(df:pd.DataFrame, assessment_id):
#     score_df:pd.DataFrame = pd.DataFrame({'assessment_id':pd.Series(dtype='int'),
#                                           'question_id':pd.Series(dtype='int'),
#                                             'student_id':pd.Series(dtype='int'), 'score':pd.Series(dtype='float')})

#     questions = df["question_id"].unique().tolist()
#     users = df["student_id"].unique().tolist()
#     for question_id in questions:
#         num_answer = df[df['question_id'] == question_id]['num_answer'].iloc[0]
#         print(num_answer)
#         mark = df[df['question_id'] == question_id]['mark'].iloc[0]
#         print(mark)
#         for user in users:
#             score = df[(df['question_id']== question_id) & (df['student_id'] == user)].sort_values(by="preds", ascending=False)['preds'][:num_answer].sum()
#             score = score/num_answer * mark
#             row = {"assessment_id":assessment_id,"question_id":question_id,
#                             "student_id":user,"score":score}
#             score_df = score_df.append(row, ignore_index = True)

#     return score_df

# def mark_single_nlp(df, ref_answer_key, stu_answer_key):
#     y_preds = predict.predict(df, ref_answer_key, stu_answer_key)
#     df['score'] = df['mark'] * (y_preds/2)
#     columns = ['assessment_id', 'question_id', 'student_id', 'score']
#     return df[columns]
