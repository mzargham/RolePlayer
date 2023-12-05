from dataclasses import dataclass, field
from typing import List

import requests
from os import environ
import re

@dataclass
class Llm:
    model_identifier: str = "gpt-4-1106-preview"
    url: str = "https://api.openai.com/v1/chat/completions"
    role: str = "user"
    # Use default_factory for the mutable default value
    auth: dict = field(default_factory=lambda: {"Authorization": f"Bearer {environ.get('OPENAI_API_KEY')}"})

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

    def prompt(self, text: str) -> str:

        textwithcontext = f"Given your experiences as {self.name}, {self.context}\n {text}"

        return self.llm.prompt(textwithcontext)
    
    def set_context(self, text: str):
        self.context = text

    def update_context(self, text: str):
        self.context += text

    def sensemake(self):
        thinking = self.llm.prompt(f"{self.context} given your experiences as {self.name}, what are you thinking now?")
        thought = self.llm.prompt(thinking)
        self.update_context(f"{self.name}[thinking]: {thought}")

    def dump(self):
        return f"{self.name}: {self.context}"

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
    ensemble: List[Agent] = field(default_factory=list)  # Updated
    lines: List[Line] = field(default_factory=list)  # Updated

    def append_line(self, line: Line):
        raw_line = line.dump()
        for agent in self.ensemble:
            agent.update_context(raw_line)
            agent.sensemake()

        self.lines.append(line)

    def dump(self):
        return f"{self.name}: ({self.setting})\n" + "\n".join([line.dump() for line in self.lines])

@dataclass
class Story:
    name: str
    description: str
    director: Agent = None
    cast: List[Agent] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)

    def hire_director(self, llm: Llm= Llm()):
        self.director = Agent("director", llm, f"The name of this production is:\, {self.name} \n  the desription of this production is:\n {self.description}")

    def create_cast(self):
        raw_cast = self.director.prompt(f"who is in the cast? Please list the characters in the cast; names should contain no spaces and there should be no duplicates; use the @ symbol to denote the names and separate them with commas")
        cast = re.findall(r'@(\w+)', raw_cast)

        for agent in cast:
            private_backstory = self.director.prompt(f"what is {agent}'s private backstory? Be clear about their values, their goals, their fears, and their relationships with other characters.")
            self.cast.append(Agent(agent, Llm(), private_backstory))

    def get_agent_by_name(self, name: str) -> Agent:
        for agent in self.cast:
            if agent.name == name:
                return agent
        return None

    def new_scene(self) -> Scene:
        self.director.set_context(self.dump())
        print("director context")
        print(self.director.context)
        raw_name = self.director.prompt(f"what is the name of the next scene? Please put the name in brackets, eg [scene name]")
        raw_setting = self.director.prompt(f"what is the setting of the next scene?")
        raw_ensemble = self.director.prompt(f"who is in the next scene? Please list the characters in the scene, use the @ symbol to denote the names and separate them with commas")
        
        # Extract the name of the scene from brackets
        name_match = re.search(r'\[(.*?)\]', raw_name)
        name = name_match.group(1) if name_match else "Unnamed Scene"

        # Extract the setting of the scene
        setting = raw_setting if raw_setting else "Undefined Setting"

        # Extract the ensemble of the scene
        ensemble = re.findall(r'@(\w+)', raw_ensemble)
        ensemble_agents = [self.get_agent_by_name(agent_name) for agent_name in ensemble if self.get_agent_by_name(agent_name)]

        return Scene(name, setting, ensemble_agents, [])

    def new_line(self, scene: Scene) -> Line:
        raw_speaker = self.director.prompt(f"who is speaking? Please use the @ symbol to denote the name of the speaker")
        speaker_name_match = re.search(r'@(\w+)', raw_speaker)
        speaker_name = speaker_name_match.group(1) if speaker_name_match else "Unknown Speaker"
        speaker = self.get_agent_by_name(speaker_name)

        raw_text = self.director.prompt(f"what do you, {speaker_name}, say?")

        return Line(speaker, raw_text)
    
    def append_scene(self, scene: Scene):
        self.scenes.append(scene)

    def scene_over(self, scene: Scene) -> bool:
        if len(scene.lines) == 0:
            return False
        elif len(scene.lines) > 10:
            return True
        else:
            raw = self.director.prompt(f"is {scene.name} over? please respond clearly with 'yes' or 'no'")

            # Use regex to find 'yes' or 'no' in the response
            match_yes = re.search(r'\byes\b', raw, re.IGNORECASE)
            match_no = re.search(r'\bno\b', raw, re.IGNORECASE)

            if match_yes:
                return True
            elif match_no:
                return False
            else:
                # Handle cases where the response is not clear
                # You might want to raise an exception or return a default value
                raise ValueError("The response is not clear: 'yes' or 'no' was not found")
        
    def story_over(self) -> bool:
        if len(self.scenes) == 0:
            return False
        elif len(self.scenes) > 5:
            return True
        else:
            raw = self.director.prompt(f"Do we need to start another scene? please respond clearly with 'yes' or 'no'")

            print(raw)

            # Use regex to find 'yes' or 'no' in the response
            match_yes = re.search(r'\byes\b', raw, re.IGNORECASE)
            match_no = re.search(r'\bno\b', raw, re.IGNORECASE)

            if match_yes:
                return False
            elif match_no:
                return True
            else:
                # Handle cases where the response is not clear
                # You might want to raise an exception or return a default value
                raise ValueError("The response is not clear: 'yes' or 'no' was not found")


    def dump(self):
        cast_text = "\n".join([agent.name for agent in self.cast])

        return f"{self.name} by {self.director.llm.model_identifier}\n Cast:\n" + cast_text + "\n" + "\n".join([scene.dump() for scene in self.scenes])
    
    def save(self, filename: str):
        with open(filename, "w") as f:
            f.write(self.dump())
    
    def play(self, verbose: bool = False):

        if self.director is None:
            self.hire_director()
            if verbose:
                print(f"Hired director named {self.director.llm.model_identifier}")
        if self.cast == []:
            self.create_cast()
            if verbose:
                print(f"Created cast with {len(self.cast)} characters")
                print(f"Cast: {[agent.name for agent in self.cast]}")
    
        while not self.story_over():
            scene = self.new_scene()
            if verbose:
                print(f"Created scene named {scene.name}")
                print(f"Scene setting: {scene.setting}")
            while not self.scene_over(scene):
                line = self.new_line(scene)
                scene.append_line(line)
                if verbose:
                    print(line.dump())
            self.append_scene(scene)
        
        #if verbose:
        #    print(self.dump())

#test
name = "The Wizard and the Robot"
description = "The Wizard and the Robot is a 3 scene play involving 2 characters. It is in the style of Socratic dialogue. The first scene takes place in a Medival Castle, the Wizard's home. The Robot asks the Wizard 3 questions. The second scence takes place in a futuristic setting. The Robot again asks the Wizard 3 questions. In the third and final scene the Wizard and the Robot are revealed to be talking through time-wormhole. The wizard begin's to ask questions, the Robot doesn't want to reveal anything that will harm the past, when the Wizard asks a question that the Robot feels is dangerous, he abruptly closes the time-wormhole, ending the play."
twatr = Story(name=name,description=description)
twatr.play(verbose=True)
