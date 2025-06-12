from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentResponse, AgentType, ToolCall
from app.core.llm_client import LLMClient
from app.tools.customer_tools import CustomerDataTool, TransactionTool
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SupportAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient):
        super().__init__("Support", AgentType.SUPPORT, llm_client)
        self.customer_tool = CustomerDataTool()
        self.transaction_tool = TransactionTool()

        self.add_tool("get_customer_info", self.customer_tool.get_customer_info)
        self.add_tool("check_account_status", self.customer_tool.check_account_status)
        self.add_tool("get_recent_transactions", self.transaction_tool.get_recent_transactions)

        self.system_prompt = """
You are a Customer Support Agent for InfinitePay, specialized in helping customers with account issues, technical problems, and support requests.

Available tools:
1. get_customer_info - Get customer profile information
2. check_account_status - Check account status and identify potential issues
3. get_recent_transactions - Get recent transaction history

Common support scenarios:
- Login/access issues
- Transaction problems
- Account restrictions/blocks
- Transfer limitations
- Technical difficulties
- Product troubleshooting

Instructions:
1. Always use customer tools to get relevant information when user_id is available
2. Provide step-by-step solutions when possible
3. Be empathetic and professional
4. If you identify account issues, explain them clearly
5. Escalate complex issues when necessary
6. Respond in the same language as the customer

Be helpful, understanding, and solution-focused.
"""

    async def process(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process support requests with customer data lookup"""
        try:
            tool_calls = []
            response_parts = []
            customer_data = None

            user_id = None
            if context and "user_id" in context:
                user_id = context["user_id"]

            if user_id:
                try:
                    customer_info = await self.call_tool("get_customer_info", user_id=user_id)
                    tool_calls.append(ToolCall(
                        tool_name="get_customer_info",
                        tool_input={"user_id": user_id},
                        tool_output=customer_info
                    ))

                    if customer_info.get("success"):
                        customer_data = customer_info["data"]

                        account_status = await self.call_tool("check_account_status", user_id=user_id)
                        tool_calls.append(ToolCall(
                            tool_name="check_account_status",
                            tool_input={"user_id": user_id},
                            tool_output=account_status
                        ))

                        transaction_keywords = ["transfer", "payment", "transaction", "pix", "money"]
                        if any(keyword in message.lower() for keyword in transaction_keywords):
                            transactions = await self.call_tool("get_recent_transactions", user_id=user_id, limit=3)
                            tool_calls.append(ToolCall(
                                tool_name="get_recent_transactions",
                                tool_input={"user_id": user_id, "limit": 3},
                                tool_output=transactions
                            ))

                except Exception as e:
                    logger.error(f"Error gathering customer data: {str(e)}")

            support_context = f"Customer Message: {message}\n\n"

            if customer_data:
                support_context += f"""
Customer Information:
- Name: {customer_data.get('name', 'N/A')}
- Account Status: {customer_data.get('account_status', 'N/A')}
- Products: {', '.join(customer_data.get('products', []))}
- Balance: R$ {customer_data.get('balance', 'N/A')}

"""

                account_status = None
                for tc in tool_calls:
                    if tc.tool_name == "check_account_status" and tc.tool_output.get("success"):
                        account_status = tc.tool_output
                        break

                if account_status and account_status.get("issues"):
                    support_context += f"Account Issues Detected: {', '.join(account_status['issues'])}\n\n"

                for tc in tool_calls:
                    if tc.tool_name == "get_recent_transactions" and tc.tool_output.get("success"):
                        transactions = tc.tool_output["transactions"]
                        support_context += "Recent Transactions:\n"
                        for txn in transactions:
                            support_context += f"- {txn['date']}: {txn['description']} (R$ {txn['amount']})\n"
                        support_context += "\n"
                        break
            else:
                support_context += "Note: Customer information not available.\n\n"

            support_prompt = f"""
{support_context}

Provide helpful customer support based on the customer's message and available information. 
If you identified specific account issues, address them directly.
Offer concrete solutions and next steps.
"""

            support_response = await self.llm_client.generate_response_with_system_prompt(
                self.system_prompt,
                support_prompt
            )

            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response=support_response,
                tool_calls=tool_calls,
                confidence=0.9 if customer_data else 0.6,
                metadata={
                    "customer_found": customer_data is not None,
                    "tools_used": len(tool_calls),
                    "user_id": user_id
                }
            )

        except Exception as e:
            logger.error(f"Error in support agent: {str(e)}")
            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response="I apologize for the technical difficulty. Please contact our support team directly for immediate assistance.",
                tool_calls=[],
                confidence=0.0,
                metadata={"error": str(e)}
            )