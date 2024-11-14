
import streamlit as st
import requests as r
import json
import asyncio
import aiohttp
import webbrowser

async def async_get(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.text()

async def async_post(url, headers, json_data):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_data) as response:
            return await response.text()

def authenticate(token):
    head = {
        "Authorization": f"Bearer {token}",
        "Referer": "https://tesseractonline.com/"
    }
    response = r.get("https://api.tesseractonline.com/studentmaster/subjects/4/6", headers=head).text
    data = json.loads(response)
    if data['Error'] == False:
        return head
    else:
        st.error('The given token is expired or may be wrong.')
        return None

@st.cache_data
def get_dashboard(head):
    url = "https://api.tesseractonline.com/studentmaster/subjects/4/6"
    response = r.get(url, headers=head).text
    subjects = json.loads(response)['payload']
    return {subject['subject_id']: subject['subject_name'] for subject in subjects}

@st.cache_data
def get_units(subject_id, head):
    url = f"https://api.tesseractonline.com/studentmaster/get-subject-units/{subject_id}"
    response = r.get(url, headers=head).text
    units = json.loads(response)['payload']
    return {unit['unitId']: unit['unitName'] for unit in units}

@st.cache_data
def get_topics(unit_id, head):
    url = f"https://api.tesseractonline.com/studentmaster/get-topics-unit/{unit_id}"
    response = r.get(url, headers=head).text
    topics = json.loads(response)['payload']['topics']
    return {
        f"{topic['id']}. {topic['name']}  {topic['learningFlag']}": {
            'video': topic['videourl']
        } for topic in topics
    }

async def write_quiz(i, head):
    try:
        quiz_data = json.loads(await async_get(f"https://api.tesseractonline.com/quizattempts/create-quiz/{i}", head))
        quiz_id = quiz_data["payload"]['quizId']
        questions = quiz_data["payload"]["questions"]
        options = ['a', 'b', 'c', 'd']
        previous_score = json.loads(await async_post(
            "https://api.tesseractonline.com/quizattempts/submit-quiz",
            head,
            {
                "branchCode": "NGIT-CSM",
                "sectionName": "NGIT-CSM-PS1",
                "quizId": f'{quiz_id}'
            }
        ))["payload"]["score"]
        
        st.write("Work in progress, please wait...")
        for question in questions:
            for option in options:
                await async_post(
                    "https://api.tesseractonline.com/quizquestionattempts/save-user-quiz-answer",
                    head,
                    {
                        "quizId": f'{quiz_id}',
                        "questionId": f"{question['questionId']}",
                        "userAnswer": f'{option}'
                    }
                )
                score = json.loads(await async_post(
                    "https://api.tesseractonline.com/quizattempts/submit-quiz",
                    head,
                    {
                        "branchCode": "NGIT-CSM",
                        "sectionName": "NGIT-CSM-PS1",
                        "quizId": f'{quiz_id}'
                    }
                ))["payload"]["score"]
                if score == 5:
                    st.success('Test completed, refresh the page.')
                    return
                if score > previous_score:
                    previous_score = score
                    break
    except KeyError:
        st.error('This subject or topic is inactive.')

async def write_quiz_for_all_topics(selected_topics, head):
    for topic in selected_topics:
        await write_quiz(topic.split('.')[0], head)

def main():
    st.title('Tesseract Quiz Automation')
    
    token = st.text_input('Enter token:', type='password')
    if token:
        head = authenticate(token)
        if head:
            subjects = get_dashboard(head)
            subject_choice = st.selectbox('Select subject:', list(subjects.values()))
            
            if subject_choice:
                subject_id = list(subjects.keys())[list(subjects.values()).index(subject_choice)]
                units = get_units(subject_id, head)
                unit_choice = st.selectbox('Select unit:', list(units.values()))
                
                if unit_choice:
                    unit_id = list(units.keys())[list(units.values()).index(unit_choice)]
                    topics = get_topics(unit_id, head)
                    
                    selected_topics = st.multiselect('Select topics:', list(topics.keys()))
                    
                    if st.button('Start Quiz'):
                        asyncio.run(write_quiz_for_all_topics(selected_topics, head))  # Modified to select all topics

if __name__ == "__main__":
    main()
