"""
AI Idea Planner - Converts natural language ideas into structured tasks
"""

import json
import re
from typing import List, Dict, Any
from pydantic import BaseModel


class TaskIdea(BaseModel):
    title: str
    prompt: str
    model: str = "auto"
    priority: int = 5
    dependencies: List[int] = []


class TaskPlan(BaseModel):
    description: str
    tasks: List[TaskIdea]


class AIIdeaPlanner:
    """
    AI-powered idea to task converter.
    Uses LLM to parse user ideas and generate structured task plans.
    """

    def __init__(self, nvidia_api_key: str = None):
        self.nvidia_api_key = nvidia_api_key
        self.model = "meta/llama-3.1-70b-instruct"

    async def parse_idea(self, user_message: str) -> Dict[str, Any]:
        """
        Parse a user's idea and return a structured task plan.
        """
        prompt = f"""You are an expert task planner for OneQueue, a distributed task processing system.
Your job is to convert user ideas into structured, actionable tasks.

User's idea: "{user_message}"

Break this down into specific, executable tasks. For each task, provide:
1. A clear, descriptive title
2. A detailed prompt that can be executed
3. The appropriate model (choose from: microsoft/phi-3-mini-4k-instruct, meta/llama-3.1-70b-instruct, google/gemma-7b-it)
4. Priority (1-10, where 10 is highest)
5. Any dependencies (task IDs that must complete first)

Return your response in this EXACT JSON format:
{{
  "description": "Brief summary of what you're creating",
  "tasks": [
    {{
      "title": "Task title",
      "prompt": "Detailed instructions for this task",
      "model": "model-name",
      "priority": 5,
      "dependencies": []
    }}
  ]
}}

IMPORTANT:
- Break complex ideas into multiple sequential tasks
- Each task should be atomic and independently executable
- Use dependencies to order tasks correctly
- Be specific in prompts - include all necessary context
- If the idea is unclear, ask clarifying questions in the description

Example for "I want to analyze 100 tweets and create a sentiment report":
{{
  "description": "Creating a sentiment analysis pipeline for tweets",
  "tasks": [
    {{
      "title": "Fetch and preprocess tweets",
      "prompt": "Retrieve 100 tweets from the database, clean text (remove URLs, mentions, hashtags), and prepare for analysis",
      "model": "microsoft/phi-3-mini-4k-instruct",
      "priority": 8,
      "dependencies": []
    }},
    {{
      "title": "Analyze sentiment for each tweet",
      "prompt": "For each tweet, determine if sentiment is positive, negative, or neutral. Provide confidence score.",
      "model": "meta/llama-3.1-70b-instruct",
      "priority": 8,
      "dependencies": [0]
    }},
    {{
      "title": "Generate sentiment report",
      "prompt": "Create a comprehensive report with sentiment distribution, key insights, and examples",
      "model": "meta/llama-3.1-70b-instruct",
      "priority": 7,
      "dependencies": [1]
    }}
  ]
}}

Now analyze the user's idea and return ONLY valid JSON:"""

        try:
            # Call NVIDIA API to parse the idea
            response = await self._call_llm(prompt)

            # Parse the response
            plan_data = self._extract_json(response)
            if not plan_data:
                return {
                    "response": "I couldn't understand that idea clearly. Could you rephrase it or provide more details?",
                    "taskPlan": None,
                }

            # Validate and convert to TaskPlan
            plan = TaskPlan(**plan_data)

            # Return formatted response
            return {
                "response": f"Great idea! I've broken it down into {len(plan.tasks)} tasks:\n\n{plan.description}",
                "taskPlan": {
                    "description": plan.description,
                    "tasks": [task.dict() for task in plan.tasks],
                },
            }

        except Exception as e:
            return {
                "response": f"Sorry, I encountered an error: {str(e)}. Try rephrasing your idea.",
                "taskPlan": None,
            }

    async def _call_llm(self, prompt: str) -> str:
        """Call NVIDIA LLM API"""
        import httpx

        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.3,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

        return result["choices"][0]["message"]["content"]

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        # Try to find JSON in the response
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        # If no JSON found, try to parse the whole text
        try:
            return json.loads(text)
        except:
            return None


# Global instance
planner = None


def get_planner() -> AIIdeaPlanner:
    global planner
    if planner is None:
        import os

        nvidia_key = os.getenv("NVIDIA_API_KEY", "")
        planner = AIIdeaPlanner(nvidia_api_key=nvidia_key)
    return planner
