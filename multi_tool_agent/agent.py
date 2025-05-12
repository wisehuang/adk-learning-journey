from google.adk.agents import Agent

root_agent = Agent(
    name="hello_agent",
    model="gemini-2.5-pro-preview-05-06",
    instruction="你是一個友善的助理，回答用戶問題。"
)
