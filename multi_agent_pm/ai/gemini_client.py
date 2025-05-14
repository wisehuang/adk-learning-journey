"""Gemini integration for natural language understanding in agents.

This module provides a client for Google's Gemini API to enable agents to understand
natural language commands and make intelligent decisions.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini client.
        
        Args:
            api_key: The API key for Gemini. If not provided, will attempt to use
                the GEMINI_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("No Gemini API key provided. Natural language features will be unavailable.")
            logger.warning("Please set GEMINI_API_KEY in your .env file or environment variables.")
            self.enabled = False
            return
            
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro-preview-05-06')
        self.enabled = True
        logger.info("Gemini client initialized successfully")
        
    async def understand_command(self, 
                                text: str, 
                                agent_type: str, 
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a natural language command and convert it to a structured operation.
        
        Args:
            text: The natural language command text.
            agent_type: The type of agent ("manager", "engineer", "tester").
            context: Optional context information to help with understanding.
            
        Returns:
            A dictionary containing the structured command information.
        """
        if not self.enabled:
            # Fallback to basic command processing if Gemini is not available
            return self._basic_command_parsing(text, agent_type)
            
        # Create a prompt for Gemini based on agent type
        prompt = self._create_prompt(text, agent_type, context)
        
        try:
            # Generate a response from Gemini
            response = await self.model.generate_content_async(prompt)
            
            # Parse the response to extract structured command
            return self._parse_gemini_response(response.text, agent_type)
        except Exception as e:
            logger.error(f"Error using Gemini API: {str(e)}")
            # Fallback to basic command processing
            return self._basic_command_parsing(text, agent_type)
    
    def _create_prompt(self, 
                       text: str, 
                       agent_type: str, 
                       context: Optional[Dict[str, Any]] = None) -> str:
        """Create a prompt for Gemini based on agent type and context.
        
        Args:
            text: The natural language command text.
            agent_type: The type of agent.
            context: Optional context information.
            
        Returns:
            A formatted prompt string.
        """
        base_prompt = f"""As a {agent_type} agent in a project management system, 
        interpret the following command and extract the relevant operation and parameters.
        
        Command: "{text}"
        
        Output the result as a JSON object with 'operation' and 'parameters' fields.
        """
        
        if context:
            context_str = "\n\nContext information:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
            base_prompt += context_str
            
        return base_prompt
    
    def _parse_gemini_response(self, response_text: str, agent_type: str) -> Dict[str, Any]:
        """Parse the response from Gemini into a structured command.
        
        Args:
            response_text: The raw text response from Gemini.
            agent_type: The agent type for fallback parsing.
            
        Returns:
            A structured command dictionary.
        """
        try:
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON-like content in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return result
            
            # If no JSON found, treat the entire response as the operation
            return {"operation": response_text.strip(), "parameters": {}}
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            return self._basic_command_parsing(response_text, agent_type)
    
    def _basic_command_parsing(self, text: str, agent_type: str) -> Dict[str, Any]:
        """Fallback method for basic command parsing without AI.
        
        Args:
            text: The command text.
            agent_type: The agent type.
            
        Returns:
            A basic parsed command.
        """
        # Simple keyword-based parsing for common commands
        text = text.lower().strip()
        operation = None
        parameters = {}
        
        # Extract task ID if present (format: TASK-12345678)
        import re
        task_id_match = re.search(r'(TASK-\d+)', text)
        if task_id_match:
            parameters["task_id"] = task_id_match.group(1)
        
        # Parse based on agent type
        if agent_type == "manager":
            if "create task" in text:
                operation = "create_task"
                # Try to extract title and description
                title_match = re.search(r'"([^"]+)"', text)
                if title_match:
                    parameters["title"] = title_match.group(1)
                    # Look for a second quoted string for description
                    remaining_text = text[text.find(title_match.group(0)) + len(title_match.group(0)):]
                    desc_match = re.search(r'"([^"]+)"', remaining_text)
                    if desc_match:
                        parameters["description"] = desc_match.group(1)
            elif "assign task" in text:
                operation = "assign_task"
            elif "list tasks" in text:
                operation = "list_tasks"
            elif "review task" in text:
                operation = "review_task"
                if "approve" in text:
                    parameters["approve"] = True
                elif "reject" in text:
                    parameters["approve"] = False
            elif "agent status" in text or "status" in text:
                operation = "get_agent_status"
        
        elif agent_type == "engineer":
            if "my tasks" in text:
                operation = "list_my_tasks"
            elif "work on" in text:
                operation = "work_on_task"
            elif "complete task" in text:
                operation = "complete_task"
            elif "status" in text:
                operation = "get_status"
        
        elif agent_type == "tester":
            if "completed tasks" in text:
                operation = "list_completed_tasks"
            elif "test task" in text:
                operation = "test_task"
            elif "my tasks" in text:
                operation = "list_my_tasks"
            elif "submit test" in text or "submit results" in text:
                operation = "submit_test_results"
                if "fail" in text or "failed" in text:
                    parameters["passed"] = False
                else:
                    parameters["passed"] = True
            elif "status" in text:
                operation = "get_status"
        
        if not operation:
            operation = "unknown"
            parameters["original_text"] = text
            
        return {"operation": operation, "parameters": parameters} 