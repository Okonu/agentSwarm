from typing import Dict, Any, List, Optional
import random
import logging

logger = logging.getLogger(__name__)


class CustomerDataTool:

    def __init__(self):
        self.customers = {
            "client789": {
                "user_id": "client789",
                "name": "João Silva",
                "email": "joao.silva@email.com",
                "phone": "+55 11 99999-9999",
                "account_status": "active",
                "products": ["maquininha_smart", "conta_digital"],
                "last_transaction": "2024-01-15",
                "balance": 1250.50,
                "limits": {
                    "daily_transfer": 5000.00,
                    "monthly_transfer": 50000.00
                }
            }
        }

    async def get_customer_info(self, user_id: str) -> Dict[str, Any]:
        try:
            customer = self.customers.get(user_id)
            if customer:
                return {"success": True, "data": customer}
            else:
                return {"success": False, "error": "Customer not found"}
        except Exception as e:
            logger.error(f"Error getting customer info: {str(e)}")
            return {"success": False, "error": str(e)}

    async def check_account_status(self, user_id: str) -> Dict[str, Any]:
        try:
            customer = self.customers.get(user_id)
            if not customer:
                return {"success": False, "error": "Customer not found"}

            issues = []

            if customer["account_status"] != "active":
                issues.append("Account is not active")

            possible_issues = [
                "Daily transfer limit reached",
                "Pending document verification",
                "Suspicious activity detected",
                "Card temporarily blocked"
            ]

            if random.random() < 0.3:
                issues.append(random.choice(possible_issues))

            return {
                "success": True,
                "account_status": customer["account_status"],
                "issues": issues,
                "last_transaction": customer["last_transaction"]
            }

        except Exception as e:
            logger.error(f"Error checking account status: {str(e)}")
            return {"success": False, "error": str(e)}


class TransactionTool:

    async def get_recent_transactions(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        try:
            mock_transactions = [
                {
                    "id": "txn_001",
                    "date": "2024-01-15",
                    "type": "payment_received",
                    "amount": 150.00,
                    "description": "Venda - Cartão de Crédito"
                },
                {
                    "id": "txn_002",
                    "date": "2024-01-14",
                    "type": "transfer",
                    "amount": -50.00,
                    "description": "Transferência PIX"
                },
                {
                    "id": "txn_003",
                    "date": "2024-01-13",
                    "type": "payment_received",
                    "amount": 300.00,
                    "description": "Venda - Maquininha"
                }
            ]

            return {"success": True, "transactions": mock_transactions[:limit]}

        except Exception as e:
            logger.error(f"Error getting transactions: {str(e)}")
            return {"success": False, "error": str(e)}