from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import autogen
from autogen import AssistantAgent, UserProxyAgent
import xml.etree.ElementTree as ET
import sys
import io

app = Flask(__name__)

# Initialize AutoGen agents
config_list = autogen.config_list_from_json(
    "./OAI_CONFIG_LIST.json"  # All needed OpenAI info is in this file
)

llm_config = {
    "timeout": 600,
    "cache_seed": 44,  # change the seed for different trials
    "config_list": config_list,
    "temperature": 0,
}

assistant = AssistantAgent(
    name="summarizer",
    llm_config=llm_config,
    human_input_mode="NEVER",
    system_message="""
    You are the Cloud Solution Architect. 
    Please categorize papers after seeing their abstracts printed and create a JSON list with Domain, Title, Authors, Summary and Link.""",
    is_termination_msg=lambda x: True,
)

user_proxy = UserProxyAgent(
    "user_proxy", 
    code_execution_config=False,
    human_input_mode="NEVER",
    system_message="""Once a JSON file received, return it immediately.""",
    #is_termination_msg=lambda x: True,
)

'''
groupchat = autogen.GroupChat(
    agents=[assistant, user_proxy],
    messages=[],
    speaker_selection_method="round_robin",  # With two agents, this is equivalent to a 1:1 conversation.
    allow_repeat_speaker=False,
    max_round=8,
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config,
)
'''

def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = ' '.join([p.text for p in soup.find_all('p')])
    return text

def get_last_elements(d):
    return {k: v[-1] for k, v in d.items()}

@app.route('/summarize', methods=['POST'])
def summarize():
    url = request.json.get('url')
    query = request.json.get('query')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    else:
        print(f"Scraping website: {url}")
        
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    else:
        print(f"Query: {query}")

    try:
        # Scrape the website
        document_text = scrape_website(url)
        # Send a GET request to the arXiv API
        response = requests.get(url, params=query)

        # Parse the XML response
        xml_response = response.text
        if xml_response == '':
            return jsonify({'error': 'No text found on the website'}), 400
        else:
            # Extract the relevant information from the XML response
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_response)

            # Iterate over the entries and print the title, authors, abstract, and link
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                title = entry.find("{http://www.w3.org/2005/Atom}title").text
                authors = [author.text for author in entry.findall("{http://www.w3.org/2005/Atom}author")]
                abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text
                link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

                print("Title:", title)
                print("Authors:", ", ".join(authors))
                print("Abstract:", abstract)
                print("Link:", link)
            print()
    
        # Use AutoGen agent to summarize the document
        user_proxy.initiate_chat(assistant, message=f"{xml_response}")
        
        # Capture the response from the assistant
        summary = assistant.chat_messages
        summary = list(summary.values())[0][0].get('content')
        
        
        if summary is None:
            return jsonify({'error': 'No summary found'}), 400
        else:
            return summary, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
