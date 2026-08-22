import sys
from typing import Dict, List, Literal, Optional

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

class AzureFoundryClient:
    def __init__(self, endpoint, apiKey, useEntra=False):
        try:
            if useEntra:
                self.client = ChatCompletionsClient(
                    endpoint=endpoint,
                    credential=DefaultAzureCredential(),
                    credential_scopes=["https://cognitiveservices.azure.com/.default"],
                )
            else:
                self.client = ChatCompletionsClient (
                    endpoint=endpoint,
                    credential=AzureKeyCredential(apiKey)
                )
            self.chat = Chat(self.client)
        except Exception as e:
            print(f"Error initializing Azure Foundry client: {e}")
            sys.exit(1)

class Chat:
    def __init__(self, client):
        self.completions = ChatCompletions(client)

class ChatCompletions:
    def __init__(self, client):
        self.client = client

    async def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        stream: Optional[bool] = True,
        tools: Optional[List[dict]] = None,
        tool_choice: Literal["none", "auto", "required"] = "auto",
        **kwargs,           
    ):
        return self.client.complete(
            messages=messages,
            max_tokens=max_tokens,
            model=model,
            stream=stream,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            **kwargs
        )
        

            