from dataclasses import dataclass
from typing import List

import requests
from os import environ

@dataclass
class Llm:
    model_identifier: str = "gpt-4-1106-preview"
    url: str = "https://api.openai.com/v1/chat/completions"
    role: str = "user"
    auth: dict = {"Authorization": f"Bearer {environ.get('OPENAI_API_KEY')}"}

    def prompt(self, text: str) -> str:
        """
        Method to send a prompt to the LLM and return its response.
        """
        try:
            response = requests.post(self.url, json={
                "model": self.model_identifier,
                "messages": [{"role": self.role, "content": text}]
            }, headers=self.auth)
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
            return response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        except requests.exceptions.RequestException as e:
            # Handle any request-related errors
            return f"An error occurred: {e}"

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

            try:
                response = requests.post(self.url, json={
                    "model": self.model_identifier,
                    "messages": [{"role": self.role, "content": full_prompt}]
                }, headers=self.auth)
                response.raise_for_status()

                content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                responses.append(content)

                # Update the conversation history
                conversation_history.append(prompt)
                conversation_history.append(content)
            except requests.exceptions.RequestException as e:
                # Handle any request-related errors
                responses.append(f"An error occurred: {e}")

        return responses

@dataclass
class Agent:
    name: str
    llm: Llm
    context: str

    def update_context(self, text: str):
        self.context += text

    def sensemake(self):
        thinking = self.llm.prompt(f"{self.context} given your experiences as {self.name}, what are you thinking now?")
        self.update_context(self.llm.prompt(thinking))

@dataclass
class Line:
    speaker: Agent
    text: str

    def dump(self):
        return f"{self.speaker.name}: {self.text}"

@dataclass
class Scene:
    name: str
    setting: str
    ensemble: List[Agent]
    lines: List[Line]



    def dump(self):
        return f"{self.name}: ({self.setting})\n" + "\n".join([line.dump() for line in self.lines])

@dataclass
class Story:
    name: str
    director: Agent
    cast: List[Agent]
    description: str
    scenes: List[Scene]

    def dump(self):
        cast_text = "\n".join([agent.llm.model_dentifer+" as "+agent.name for agent in self.cast])

        return f"{self.name} by {self.director.name}\n Cast" + cast_text + "\n" + "\n".join([scene.dump() for scene in self.scenes])
    
