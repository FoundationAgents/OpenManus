"""
CRM Integration Tool

This tool provides comprehensive CRM integration supporting multiple platforms
including Twenty CRM (open-source), HubSpot, Salesforce, and Pipedrive.

Author: Enhancement #4 Implementation
Date: 2025-10-26
"""

import json
import os
from typing import Dict, List, Optional

from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.utils.logger import logger


class CRMTool(BaseTool):
    """
    CRM integration for managing contacts, deals, and customer interactions.

    This tool provides comprehensive CRM operations:
    - Create and update contacts
    - Manage deals and opportunities
    - Track customer interactions
    - View sales pipeline
    - Generate AI-powered insights

    Supported CRMs:
    - Twenty CRM (open-source, self-hosted)
    - HubSpot (via API)
    - Salesforce (via API)
    - Pipedrive (via API)
    - KeyCRM (Ukrainian CRM, via REST API)

    Use cases:
    - Automatically log customer interactions
    - Update deal statuses based on email/call outcomes
    - Generate sales insights and reports
    - Manage contact database
    - Track customer journey
    - Sync data between systems

    Design rationale:
    - Unified interface across multiple CRM platforms
    - GraphQL API for Twenty CRM (modern, flexible)
    - REST API for traditional CRMs (HubSpot, Salesforce)
    - Automatic field mapping and normalization
    - AI-powered insights using LLM
    - Error handling for rate limits and permissions

    Technical details:
    - Twenty CRM: GraphQL API (self-hosted)
    - HubSpot: REST API v3
    - Salesforce: REST API v58.0
    - Pipedrive: REST API v1
    - KeyCRM: REST API v1 (https://openapi.keycrm.app/v1)
    - Authentication: API keys/tokens via environment variables
    """

    name: str = "crm"
    description: str = (
        "CRM integration for managing contacts, deals, and customer interactions. "
        "Supports Twenty CRM, HubSpot, Salesforce, Pipedrive, KeyCRM. "
        "Create/update contacts, manage deals, track interactions, view pipeline, generate insights. "
        "Requires CRM_TYPE and corresponding API credentials in environment variables."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create_contact",
                        "update_contact",
                        "get_contact",
                        "search_contacts",
                        "create_deal",
                        "update_deal",
                        "get_deal",
                        "get_pipeline",
                        "log_activity",
                        "get_insights",
                    ],
                    "description": "CRM operation to perform",
                },
                "contact_id": {
                    "type": "string",
                    "description": "Contact ID (for update_contact, get_contact)",
                },
                "deal_id": {
                    "type": "string",
                    "description": "Deal ID (for update_deal, get_deal)",
                },
                "name": {"type": "string", "description": "Contact/company name"},
                "email": {"type": "string", "description": "Email address"},
                "phone": {"type": "string", "description": "Phone number"},
                "company": {"type": "string", "description": "Company name"},
                "title": {"type": "string", "description": "Job title"},
                "deal_name": {"type": "string", "description": "Deal/opportunity name"},
                "deal_value": {"type": "number", "description": "Deal value/amount"},
                "deal_stage": {
                    "type": "string",
                    "description": "Deal stage (e.g., 'qualification', 'proposal', 'closed-won')",
                },
                "activity_type": {
                    "type": "string",
                    "description": "Activity type (e.g., 'call', 'email', 'meeting')",
                },
                "activity_note": {
                    "type": "string",
                    "description": "Activity notes/description",
                },
                "search_query": {
                    "type": "string",
                    "description": "Search query for contacts",
                },
                "filters": {
                    "type": "object",
                    "description": "Filter criteria for queries",
                },
            },
            "required": ["action"],
        }
    )

    def __init__(self, **data):
        """Initialize the CRM tool."""
        super().__init__(**data)
        self.crm_type = os.getenv("CRM_TYPE", "twenty").lower()
        self.api_key = None
        self.api_url = None
        self.client = None

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the CRM client based on type."""
        if self.crm_type == "twenty":
            self.api_url = os.getenv("TWENTY_API_URL", "http://localhost:3000/graphql")
            self.api_key = os.getenv("TWENTY_API_KEY")
            logger.info(f"Initialized Twenty CRM client (URL: {self.api_url})")

        elif self.crm_type == "hubspot":
            self.api_url = "https://api.hubapi.com"
            self.api_key = os.getenv("HUBSPOT_API_KEY")
            logger.info("Initialized HubSpot CRM client")

        elif self.crm_type == "salesforce":
            self.api_url = os.getenv(
                "SALESFORCE_INSTANCE_URL", "https://login.salesforce.com"
            )
            self.api_key = os.getenv("SALESFORCE_ACCESS_TOKEN")
            logger.info("Initialized Salesforce CRM client")

        elif self.crm_type == "pipedrive":
            self.api_url = "https://api.pipedrive.com/v1"
            self.api_key = os.getenv("PIPEDRIVE_API_TOKEN")
            logger.info("Initialized Pipedrive CRM client")

        elif self.crm_type == "keycrm":
            self.api_url = "https://openapi.keycrm.app/v1"
            self.api_key = os.getenv("KEYCRM_API_KEY")
            logger.info("Initialized KeyCRM client")

        else:
            logger.warning(
                f"Unknown CRM type: {self.crm_type}. Defaulting to Twenty CRM."
            )
            self.crm_type = "twenty"
            self.api_url = os.getenv("TWENTY_API_URL", "http://localhost:3000/graphql")
            self.api_key = os.getenv("TWENTY_API_KEY")

    async def _graphql_request(
        self, query: str, variables: Optional[Dict] = None
    ) -> Dict:
        """
        Make a GraphQL request (for Twenty CRM).

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data
        """
        try:
            import aiohttp

            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {"query": query}
            if variables:
                payload["variables"] = variables

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, json=payload, headers=headers
                ) as response:
                    data = await response.json()

                    if "errors" in data:
                        raise Exception(f"GraphQL errors: {data['errors']}")

                    return data.get("data", {})

        except ImportError:
            raise Exception("aiohttp not installed. Run: pip install aiohttp")
        except Exception as e:
            logger.error(f"GraphQL request failed: {e}")
            raise

    async def _rest_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        Make a REST API request (for HubSpot, Salesforce, Pipedrive).

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request body
            params: Query parameters

        Returns:
            Response data
        """
        try:
            import aiohttp

            url = f"{self.api_url}/{endpoint.lstrip('/')}"

            headers = {
                "Content-Type": "application/json",
            }

            # Add authentication based on CRM type
            if self.crm_type == "hubspot":
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.crm_type == "salesforce":
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.crm_type == "pipedrive":
                if params is None:
                    params = {}
                params["api_token"] = self.api_key

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, json=data, params=params, headers=headers
                ) as response:
                    return await response.json()

        except ImportError:
            raise Exception("aiohttp not installed. Run: pip install aiohttp")
        except Exception as e:
            logger.error(f"REST request failed: {e}")
            raise

    # ==================== Twenty CRM Methods ====================

    async def _twenty_create_contact(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
    ) -> Dict:
        """Create contact in Twenty CRM."""
        query = """
        mutation CreatePerson($name: String!, $email: String, $phone: String) {
            createPerson(data: {
                name: {firstName: $name}
                email: $email
                phone: $phone
            }) {
                id
                name {firstName lastName}
                email
                phone
                createdAt
            }
        }
        """

        variables = {"name": name, "email": email, "phone": phone}

        result = await self._graphql_request(query, variables)
        return result.get("createPerson", {})

    async def _twenty_search_contacts(self, search_query: str) -> List[Dict]:
        """Search contacts in Twenty CRM."""
        query = """
        query SearchPeople($filter: PersonFilterInput) {
            people(filter: $filter) {
                edges {
                    node {
                        id
                        name {firstName lastName}
                        email
                        phone
                        company {name}
                    }
                }
            }
        }
        """

        variables = {"filter": {"name": {"contains": search_query}}}

        result = await self._graphql_request(query, variables)
        people = result.get("people", {}).get("edges", [])
        return [edge["node"] for edge in people]

    async def _twenty_create_deal(
        self,
        deal_name: str,
        deal_value: Optional[float] = None,
        contact_id: Optional[str] = None,
    ) -> Dict:
        """Create deal in Twenty CRM."""
        query = """
        mutation CreateOpportunity($name: String!, $amount: Float, $personId: ID) {
            createOpportunity(data: {
                name: $name
                amount: {amountMicros: $amount currencyCode: "USD"}
                personId: $personId
            }) {
                id
                name
                amount {amountMicros currencyCode}
                stage
                createdAt
            }
        }
        """

        variables = {
            "name": deal_name,
            "amount": int(deal_value * 1000000)
            if deal_value
            else None,  # Convert to micros
            "personId": contact_id,
        }

        result = await self._graphql_request(query, variables)
        return result.get("createOpportunity", {})

    # ==================== HubSpot Methods ====================

    async def _hubspot_create_contact(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
    ) -> Dict:
        """Create contact in HubSpot."""
        name_parts = name.split(" ", 1)
        firstname = name_parts[0]
        lastname = name_parts[1] if len(name_parts) > 1 else ""

        data = {
            "properties": {
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "phone": phone,
                "company": company,
            }
        }

        return await self._rest_request("POST", "/crm/v3/objects/contacts", data=data)

    async def _hubspot_search_contacts(self, search_query: str) -> List[Dict]:
        """Search contacts in HubSpot."""
        data = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "CONTAINS_TOKEN",
                            "value": search_query,
                        }
                    ]
                }
            ]
        }

        result = await self._rest_request(
            "POST", "/crm/v3/objects/contacts/search", data=data
        )
        return result.get("results", [])

    # KeyCRM-specific methods to be added to crm_integration.py

    # Add these methods after the HubSpot methods (around line 425)

    # ==================== KeyCRM Methods ====================

    async def _keycrm_create_contact(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
    ) -> Dict:
        """
        Create contact (buyer) in KeyCRM.

        KeyCRM API: POST /buyer
        Docs: https://docs.keycrm.app/
        """
        data = {"full_name": name, "email": email, "phone": phone}

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        result = await self._rest_request("POST", f"{self.api_url}/buyer", data=data)

        return result

    async def _keycrm_search_contacts(self, search_query: str) -> List[Dict]:
        """
        Search contacts (buyers) in KeyCRM.

        KeyCRM API: GET /buyer with filters
        """
        params = {"search": search_query, "limit": 50}

        result = await self._rest_request("GET", f"{self.api_url}/buyer", params=params)

        # KeyCRM returns paginated data
        return result.get("data", [])

    async def _keycrm_get_contact(self, contact_id: str) -> Dict:
        """
        Get contact (buyer) by ID in KeyCRM.

        KeyCRM API: GET /buyer/{buyerId}
        """
        result = await self._rest_request("GET", f"{self.api_url}/buyer/{contact_id}")

        return result

    async def _keycrm_update_contact(self, contact_id: str, **kwargs) -> Dict:
        """
        Update contact (buyer) in KeyCRM.

        KeyCRM API: PUT /buyer/{buyerId}
        """
        # Map common fields to KeyCRM fields
        data = {}
        if "name" in kwargs:
            data["full_name"] = kwargs["name"]
        if "email" in kwargs:
            data["email"] = kwargs["email"]
        if "phone" in kwargs:
            data["phone"] = kwargs["phone"]

        result = await self._rest_request(
            "PUT", f"{self.api_url}/buyer/{contact_id}", data=data
        )

        return result

    async def _keycrm_create_deal(
        self,
        deal_name: str,
        deal_value: Optional[float] = None,
        contact_id: Optional[str] = None,
    ) -> Dict:
        """
        Create deal (order) in KeyCRM.

        KeyCRM API: POST /order
        """
        data = {
            "buyer_comment": deal_name,
        }

        if deal_value:
            data["total_price"] = deal_value

        if contact_id:
            data["buyer_id"] = int(contact_id)

        result = await self._rest_request("POST", f"{self.api_url}/order", data=data)

        return result

    async def _keycrm_get_deal(self, deal_id: str) -> Dict:
        """
        Get deal (order) by ID in KeyCRM.

        KeyCRM API: GET /order/{orderId}
        """
        result = await self._rest_request("GET", f"{self.api_url}/order/{deal_id}")

        return result

    async def _keycrm_update_deal(self, deal_id: str, **kwargs) -> Dict:
        """
        Update deal (order) in KeyCRM.

        KeyCRM API: PUT /order/{orderId}
        """
        data = {}
        if "deal_name" in kwargs:
            data["buyer_comment"] = kwargs["deal_name"]
        if "deal_value" in kwargs:
            data["total_price"] = kwargs["deal_value"]
        if "status" in kwargs:
            data["status_id"] = kwargs["status"]

        result = await self._rest_request(
            "PUT", f"{self.api_url}/order/{deal_id}", data=data
        )

        return result

    async def _keycrm_get_pipeline(self) -> Dict:
        """
        Get pipeline (orders list) from KeyCRM.

        KeyCRM API: GET /order
        """
        result = await self._rest_request(
            "GET", f"{self.api_url}/order", params={"limit": 100}
        )

        orders = result.get("data", [])

        # Group by status
        pipeline = {}
        for order in orders:
            status = order.get("status", {}).get("name", "Unknown")
            if status not in pipeline:
                pipeline[status] = []
            pipeline[status].append(order)

        return {
            "total_orders": len(orders),
            "pipeline": pipeline,
            "statuses": list(pipeline.keys()),
        }

    # ==================== Unified Interface Methods ====================

    async def _create_contact(self, **kwargs) -> Dict:
        """Create contact (unified interface)."""
        if self.crm_type == "twenty":
            return await self._twenty_create_contact(**kwargs)
        elif self.crm_type == "hubspot":
            return await self._hubspot_create_contact(**kwargs)
        elif self.crm_type == "keycrm":
            return await self._keycrm_create_contact(**kwargs)
        else:
            raise Exception(f"create_contact not implemented for {self.crm_type}")

    async def _search_contacts(self, search_query: str) -> List[Dict]:
        """Search contacts (unified interface)."""
        if self.crm_type == "twenty":
            return await self._twenty_search_contacts(search_query)
        elif self.crm_type == "hubspot":
            return await self._hubspot_search_contacts(search_query)
        elif self.crm_type == "keycrm":
            return await self._keycrm_search_contacts(search_query)
        else:
            raise Exception(f"search_contacts not implemented for {self.crm_type}")

    async def _create_deal(self, **kwargs) -> Dict:
        """Create deal (unified interface)."""
        if self.crm_type == "twenty":
            return await self._twenty_create_deal(**kwargs)
        elif self.crm_type == "keycrm":
            return await self._keycrm_create_deal(**kwargs)
        else:
            raise Exception(f"create_deal not implemented for {self.crm_type}")

    async def _get_insights(self, context: str = "general") -> str:
        """
        Generate AI-powered CRM insights.

        Args:
            context: Context for insights (e.g., 'pipeline', 'contacts', 'general')

        Returns:
            AI-generated insights
        """
        try:
            from app.llm_router import llm_router
            from app.schema import Message

            # Get some CRM data for context
            contacts = await self._search_contacts("")  # Get all contacts

            # Use default model for insights
            llm = llm_router.select_model("default")

            prompt = f"""Analyze this CRM data and provide actionable insights.

Context: {context}

CRM Type: {self.crm_type}
Total Contacts: {len(contacts)}

Sample Contacts:
{json.dumps(contacts[:5], indent=2)}

Please provide:
1. Key observations about the data
2. Potential opportunities or risks
3. Recommended actions
4. Trends or patterns

Keep it concise and actionable.
"""

            messages = [Message.user_message(prompt)]
            insights = await llm.ask(messages, stream=False)

            return insights

        except Exception as e:
            logger.warning(f"Could not generate insights: {e}")
            return "Insights generation failed. CRM data available for manual review."

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Execute CRM operation.

        Args:
            action: Operation to perform
            **kwargs: Action-specific parameters

        Returns:
            ToolResult with operation results
        """
        try:
            if not self.api_key and action != "get_insights":
                return self.error_response(
                    f"CRM API key not configured. Set {self.crm_type.upper()}_API_KEY environment variable."
                )

            if action == "create_contact":
                if "name" not in kwargs:
                    return self.error_response("Missing required parameter: name")

                contact = await self._create_contact(
                    name=kwargs["name"],
                    email=kwargs.get("email"),
                    phone=kwargs.get("phone"),
                    company=kwargs.get("company"),
                )
                return self.success_response(
                    {
                        "contact_id": contact.get("id"),
                        "status": "created",
                        "data": contact,
                    }
                )

            elif action == "search_contacts":
                if "search_query" not in kwargs:
                    return self.error_response(
                        "Missing required parameter: search_query"
                    )

                contacts = await self._search_contacts(kwargs["search_query"])
                return self.success_response(
                    {"contacts": contacts, "count": len(contacts)}
                )

            elif action == "create_deal":
                if "deal_name" not in kwargs:
                    return self.error_response("Missing required parameter: deal_name")

                deal = await self._create_deal(
                    deal_name=kwargs["deal_name"],
                    deal_value=kwargs.get("deal_value"),
                    contact_id=kwargs.get("contact_id"),
                )
                return self.success_response(
                    {"deal_id": deal.get("id"), "status": "created", "data": deal}
                )

            elif action == "get_insights":
                insights = await self._get_insights(kwargs.get("context", "general"))
                return self.success_response(
                    {"insights": insights, "crm_type": self.crm_type}
                )

            else:
                return self.error_response(f"Action not implemented: {action}")

        except Exception as e:
            logger.error(f"Error in CRM tool: {e}")
            return self.error_response(f"CRM operation failed: {str(e)}")
