import requests
import json
import random
import time
import sys
import os

def load_cookie_from_file():
    content = ""
    with open("cookie.txt") as inf:
        for line in inf:
            line = line.strip()
            content+=line
    return content

cookie = load_cookie_from_file()

user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

class CourseEraSolver:
    def __init__(self,courseId,itemId,wait_between_in_seconds):
        self.courseId = courseId
        self.itemId = itemId
        self.wait_between_in_seconds = wait_between_in_seconds
        self.store_file_name = self.courseId+"_"+self.itemId+".json"
        
        # State Management
        self.answers = {}
        self.tmp_question_id_val_map = {}
        self.tmp_answer_id_val_map = {}
        self.tmp_answer_val_id_map = {}

        self.load_existing_answers()

        
    
    def load_existing_answers(self):
        if os.path.exists(os.getcwd()+"/"+self.store_file_name):
            print("Loading existing answers from File: ")
            self.answers=json.load(open(self.store_file_name))
            print(self.answers)

    def run(self):
        while True:
            try: 
                self.pipeline()
                print(f"[+] Sleeping for {self.wait_between_in_seconds} seconds")
            except Exception as e:
                print(str(e))
                print(f"Error Sleeping for {self.wait_between_in_seconds} seconds")
            time.sleep(self.wait_between_in_seconds)

    def make_session(self):
        url = "https://www.coursera.org/api/onDemandExamSessions.v1"

        payload = {"courseId": self.courseId, "itemId": self.itemId}

        headers = {"Connection":"keep-alive","DNT":"1","Origin":"moz-extension://248728d2-42c3-417d-abb8-4de2bcc0b3df","Accept-Encoding":"","Accept-Language":"en-US,en;q=0.5","Host":"www.coursera.org","Accept":"*/*","User-Agent":user_agent, "Cookie":cookie}

        response = requests.post(url, headers=headers,json=payload)

        print("Make Session Status Code", response.status_code)
        print(json.dumps(response.json()))
        return response.json()

    def get_questions(self,id):
        url = f"https://www.coursera.org/api/onDemandExamSessions.v1/{id}/actions"

        payload = {"argument": [], "name": "getState"}

        headers = {"Connection":"keep-alive","DNT":"1","Origin":"moz-extension://248728d2-42c3-417d-abb8-4de2bcc0b3df","Accept-Encoding":"","Accept-Language":"en-US,en;q=0.5","Host":"www.coursera.org","Accept":"*/*","User-Agent":user_agent, "Cookie":cookie}

        response = requests.post(url, headers=headers,json=payload)

        print("GetQuestions Status Code", response.status_code)
        # print(json.dumps(response.json()))
        return response.json()

    def populate_tmp_answer_map(self, entry):
        print("Populating TMP Answer Map")
        ans_entries = entry['definition']['variant']['definition']['options']
        for current in ans_entries:
            print("Answer = "+current['display']['definition']['value'])
            print("Answer ID = "+current['id'])
            self.tmp_answer_id_val_map[current['id']] = current['display']['definition']['value']
            self.tmp_answer_val_id_map[current['display']['definition']['value']] = current['id']

    def get_random_answer_id(self, entry):
        rand_no = random.randint(0,len(entry['definition']['variant']['definition']['options'])-1)
        return entry['definition']['variant']['definition']['options'][rand_no]['id']

    def get_all_answer_id_list(self,entry):
        all = []
        for current in entry['definition']['variant']['definition']['options']:
            all.append(current['id'])
        return all

    def get_mcq_sub_entry(self,entry,question_id,question):
        self.tmp_question_id_val_map[question_id] = question
        self.populate_tmp_answer_map(entry)

        print("Question is "+question)
        answer = None

        # Check if answer exists
        if question in self.answers:
            answer = self.answers[question]
        
        answer_id = None
        if answer is not None:
            try:
                answer_id = self.tmp_answer_val_id_map[answer]
            except:
                # Previous answer exists. But there are 2 answers
                answer_id = self.get_random_answer_id(entry)
        else:
            answer_id = self.get_random_answer_id(entry)

        sub_entry = {
            "questionInstance": question_id,
            "response": {
                "chosen": answer_id
            }
        }
        return sub_entry


    def get_list_of_answer_id_from_answer_list(self,answer_list):
        id_list=[]
        for answer in answer_list:
            id_list.append(self.tmp_answer_val_id_map[answer])
        return id_list

    def get_checkbox_sub_entry(self,entry,question_id,question):
        self.tmp_question_id_val_map[question_id] = question
        self.populate_tmp_answer_map(entry)

        print("Question is "+question)
        answer_list = None

        # Check if answer exists
        if question in self.answers:
            answer_list = list(self.answers[question])
        
        answer_id_list = None

        if answer_list is not None:
            try:
                answer_id_list = self.get_list_of_answer_id_from_answer_list(answer_list)
            except:
                answer_id_list = self.get_all_answer_id_list(entry)
        else:
            answer_id_list = self.get_all_answer_id_list(entry)

        sub_entry = {
            "questionInstance": question_id,
            "response": {
                "chosen": answer_id_list
            }
        }
        return sub_entry

    def get_send_question_payload(self, data):
        payload = {"name":"submitResponses","argument":{"responses":[]}}
        data = data['elements'][0]['result']['parts']
        for entry in data:
            question = entry['definition']['variant']['definition']['prompt']['definition']['value']
            question_id = entry['definition']['id']

            question_type = entry['definition']['question']['type']
            sub_entry = None
            if question_type=="mcq":
                sub_entry=self.get_mcq_sub_entry(entry,question_id,question) 
            elif question_type=="checkbox":
                sub_entry=self.get_checkbox_sub_entry(entry,question_id,question) 
            payload["argument"]["responses"].append(sub_entry)
        return payload

    def send_answers(self, questions,id):
        url = f"https://www.coursera.org/api/onDemandExamSessions.v1/{id}/actions"

        payload = self.get_send_question_payload(questions)

        headers = {"Connection":"keep-alive","DNT":"1","Origin":"moz-extension://248728d2-42c3-417d-abb8-4de2bcc0b3df","Accept-Encoding":"","Accept-Language":"en-US,en;q=0.5","Host":"www.coursera.org","Accept":"*/*","User-Agent":user_agent, "Cookie":cookie}

        response = requests.post(url, headers=headers,json=payload)

        print("SendResponse Status Code", response.status_code)
        print(json.dumps(response.json()))
        return response.json()

    def get_answers_from_ids(self, answer_id_list):
        answer_list = []
        for curr_id in answer_id_list:
            ans = self.tmp_answer_id_val_map[curr_id]
            answer_list.append(ans)
        return answer_list

    def mark_mcq_answers(self, question_id, answer_id):
        print("-----------------------------")
        print("Marking MCQ answers")
        print("-----------------------------")
        ques = self.tmp_question_id_val_map[question_id]
        ans = self.tmp_answer_id_val_map[answer_id]
        self.answers[ques] = ans

    
    def get_correct_check_box_ids_list(self, reqd_data):
        ids_list = []
        for entry in reqd_data:
            if entry['isCorrect']:
                ids_list.append(entry['id'])
        return ids_list

    def mark_checkbox_answers(self, question_id, reqd_data):
        print("-----------------------------")
        print("Marking Checkbox answers")
        print("-----------------------------")
        answer_id_list = self.get_correct_check_box_ids_list(reqd_data)
        print("-----------------------------")
        print("answer id list "+str(answer_id_list))
        print("-----------------------------")
        ques = self.tmp_question_id_val_map[question_id]

        existing_answers = []
        
        # Find existing answers
        if ques in self.answers:
            existing_answers = self.answers[ques]
        
        new_answers = self.get_answers_from_ids(answer_id_list)
        
        # Add new and old answers
        new_answers.extend(existing_answers)

        if len(new_answers)>0:
            new_answers_set = set(new_answers)
            self.answers[ques] = list(new_answers_set)


    def mark_right_answers(self, parts):
        for current in parts:
            question_id = current['definition']['id']
            answer_id = current['definition']['effectiveResponse']['response']['chosen']
            print("-----------------------------")
            print("Answer id type is "+str(type(answer_id)))
            print("-----------------------------")
            if type(answer_id) == list:
                if 'options' in current['definition']['feedback']['definition']:
                    reqd_data = current['definition']['feedback']['definition']['options']
                    self.mark_checkbox_answers(question_id, reqd_data)
            else:
                if current['definition']['feedback']['definition']['isCorrect']:
                    #Answer is right                    
                    self.mark_mcq_answers(question_id, answer_id)
                

    def pipeline(self):
        session_data = self.make_session()
        session_id = session_data['elements'][0]['id']
        questions = self.get_questions(session_id)
        open("questions.json","w").write(json.dumps(questions))
        reply = self.send_answers(questions,session_id)
        self.mark_right_answers(reply['elements'][0]['result']['parts'])
        evaluation = reply['elements'][0]['result']['evaluation']
        print(evaluation)
        
        #Save state
        open(self.store_file_name,"w").write(json.dumps(self.answers))

        if (float(evaluation['score'])/evaluation['maxScore'])>=evaluation['passingFraction']:
            exit(0)

        # Clear all Temp
        self.tmp_question_id_val_map = {}
        self.tmp_answer_id_val_map = {}
        self.tmp_answer_val_id_map = {}


if __name__ == "__main__":
    courseId = sys.argv[1]
    itemId = sys.argv[2]
    wait = int(sys.argv[3])

    obj = CourseEraSolver(courseId,itemId,wait)
    obj.run()
    