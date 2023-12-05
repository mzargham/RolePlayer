from dataclasses import dataclass
from typing import List

import requests
from os import environ

class Llm:
    def __init__(self, model_identifier: str = "gpt-4-1106-preview", 
                 url: str = "https://api.openai.com/v1/chat/completions", 
                 role: str = "user",
                 auth: dict = {"Authorization": f"Bearer {environ.get('OPENAI_API_KEY')}"}):
        
        self.model_identifier = model_identifier
        self.url = url
        self.role = role
        self.auth = auth

    #add setters and getters for the above attributes
    # Getter for model_identifier
    @property
    def model_identifier(self):
        return self._model_identifier

    # Setter for model_identifier
    @model_identifier.setter
    def model_identifier(self, value):
        self._model_identifier = value

    # Getter for url
    @property
    def url(self):
        return self._url

    # Setter for url
    @url.setter
    def url(self, value):
        self._url = value

    # Getter for role
    @property
    def role(self):
        return self._role

    # Setter for role
    @role.setter
    def role(self, value):
        self._role = value

    # Getter for auth
    @property
    def auth(self):
        return self._auth

    # Setter for auth
    @auth.setter
    def auth(self, value):
        self._auth = value
        
    def prompt(self, text: str) -> str:
        # Method to send a prompt to the LLM and return its response
        url = self.url
        req = {
            "model": self.model_identifier,
            "messages":[
                {"role": self.role, "content": text}
            ]
        }
        print(req)
        response = requests.post(url, json=req, headers=self.auth)  # Use json parameter to send the request payload as JSON
        raw =  response.json()
        try:
            return f"{response.json()['choices'][0]['message']['content']}"
        except:
            return raw
 
    def prompt_sequence(self, prompts: List[str]) -> List[str]:
        """
        Method to send a sequence of prompts to the LLM and return its responses.
        Each prompt is sent in a separate request, maintaining the conversation history.
        """
        conversation_history = []
        responses = []

        for prompt in prompts:
            # Concatenate all previous elements of the conversation for context
            full_prompt = " ".join(conversation_history + [prompt])

            # Create the request payload
            req = {
                "model": self.model_identifier,
                "messages": [{"role": self.role, "content": full_prompt}]
            }

            response = requests.post(self.url, json=req, headers=self.auth)
            raw = response.json()

            try:
                # Extract the response content
                content = raw['choices'][0]['message']['content']
                responses.append(content)
                # Update the conversation history
                conversation_history.append(prompt)
                conversation_history.append(content)
            except:
                # In case of an error, append the raw response for debugging
                responses.append(raw)

        return responses

@dataclass
class Agent:
    name: str
    llm: Llm
    context: str

@dataclass
class Line:
    speaker: Agent
    text: str

@dataclass
class Scene:
    name: str
    setting: str
    ensemble: List[Agent]
    lines: List[Line]

@dataclass
class Play:
    name: str
    director: Agent
    cast: List[Agent]
    description: str
    scenes: List[Scene]