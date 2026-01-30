# **Project Specification: API Key Management Backend**

## **1\. Overview**

This application is a **FastAPI backend** designed to act as a middleware/manager for a **LiteLLM** instance. It allows users (authenticated via OAuth2-Proxy) to generate, view, and manage their own API keys for AI model access.  
The application prioritizes fetching data directly from LiteLLM but uses a local SQLite database for historical data that cannot be retrieved from the upstream service (e.g., deleted keys).

## **2\. Tech Stack**

* **Language:** Python 3.13+  
* **Framework:** FastAPI  
* **Database:** SQLite (via SQLAlchemy or SQLModel) \- *Only for local history tracking.*  
* **HTTP Client:** httpx (for communicating with LiteLLM)  
* **Environment:** Dockerized (Application \+ LiteLLM)  
* **Testing:** Pytest (Target: \>75% coverage)  
* **CI/CD:** GitHub Actions

## **3\. Configuration & Environment Variables**

The application must load the following environment variables:

| Variable | Description | Default |
| :---- | :---- | :---- |
| LLMREQ\_PREFIX | Default /api | /api |
| LITELLM\_API\_URL | URL of the LiteLLM Docker container | http://litellm:4000 |
| LITELLM\_MASTER\_KEY | The generic master key used to authenticate admin requests to LiteLLM | \- |
| LLMREQ\_DATABASE\_URL | Connection string for SQLite | sqlite:///./app.db |
| LLMREQ\_DEFAULT\_BUDGET | Default lifetime budget cap for standard keys (USD) | 1.0 |
| LLMREQ\_LONGTERM\_KEY\_LIFETIME | Expiration duration for long-term keys (e.g., "400d") | 400d |
| LLMREQ\_LONGTERM\_KEY\_LIMIT | Maximum number of active long-term keys allowed per user | 1 |
| LLMREQ\_LONGTERM\_KEY\_BUDGET | Periodic (weekly) budget for long-term keys (USD) | 20 |
| LLMREQ\_MAX\_ACTIVE\_KEY | Maximum total number of active keys allowed per user | 10 |

## **4\. Authentication & User Provisioning**

### **4.1. Trusted Header Authentication**

The app sits behind **OAuth2-Proxy**.

1. **Middleware:** Inspect the HTTP Header x-forwarded-email.  
2. **Validation:** If the header is missing, return 401 Unauthorized.  
3. **Normalization:** Convert the email to lowercase. This value is referred to as current\_user\_id.

### **4.2. JIT User Provisioning (LiteLLM Sync)**

On every authenticated request (or via a dependency injection):

1. Check if current\_user\_id exists in LiteLLM using GET /user/info.  
2. **If User does NOT exist:**  
   * Call LiteLLM POST /user/new to create the user.  
   * Set user\_id \= lower(email).  
   * Set user\_email \= lower(email).  
   * Set default budget settings if applicable.

## **5\. Data Model & Storage Strategy**

### **5.1. Source of Truth: LiteLLM**

* **Active Keys:** Stored in LiteLLM. Fetched in real-time.  
* **User Budget:** Stored in LiteLLM. Fetched in real-time.

### **5.2. Local Storage: SQLite**

Used *only* to satisfy the requirement of showing **Previous Keys** (revoked/deleted keys) and enforcing limits on key types (e.g., long-term key limit).  
**Table: key\_history**

* id: Integer, PK  
* user\_id: String (Email)  
* litellm\_key\_id: String (The unique ID/prefix from LiteLLM)  
* key\_name: String (User provided alias)  
* key\_mask: String (e.g., sk-...1234)  
* key\_type: String (standard or long-term)  
* created\_at: Datetime  
* revoked\_at: Datetime (Nullable)  
* status: String (active, revoked)

## **6\. API Endpoints**

**Base Path:** /api

### **6.1. User Dashboard**

**GET /api/me**

* **Logic:**  
  * Call LiteLLM GET /user/info/{user\_id}.  
* **Response:**  
  * user\_id (email)  
  * max\_budget  
  * spend (Current total spend).

### **6.2. Key Management**

**GET /api/keys/active**

* **Logic:**  
  * Call LiteLLM GET /key/list (filtered by user\_id).  
  * Filter response to exclude expired/invalid keys if LiteLLM returns them.  
  * Sync/Update the local key\_history table if any discrepancies are found.  
* **Response:** List of active key objects (mask, name, created\_at, spend, type).

**GET /api/keys/history**

* **Logic:**  
  * Query local SQLite key\_history table where user\_id matches and status is 'revoked' OR revoked\_at is not null.  
* **Response:** List of historical keys.

**POST /api/keys**

* **Body:**  
  {  
    "name": "my-project-key",  
    "budget": "optional\_float",  
    "type": "standard | long-term" // Default: standard  
  }

* **Logic:**  
  1. **Check Limits:**  
     * **Global Limit:** Count total active keys. If \>= LLMREQ\_MAX\_ACTIVE\_KEY, reject.  
     * **Long-term Limit:** If type is long-term, count existing long-term keys. If \>= LLMREQ\_LONGTERM\_KEY\_LIMIT, reject.  
  2. **Call LiteLLM:**  
     * Call POST /key/generate.  
     * Payload: { "user\_id": current\_user\_id, "key\_alias": name, "max\_budget": ..., "duration": ... }  
  3. **Persist Metadata:**  
     * Save metadata to local SQLite key\_history.  
* **Response:** The full raw API key.

**DELETE /api/keys/{key\_id}**

* **Logic:**  
  1. Call LiteLLM POST /key/delete.  
  2. Update local SQLite key\_history: set status \= revoked.  
* **Response:** 200 OK.

## **7\. Business Logic Details**

### **7.1. Budget Display**

The dashboard requires "Total used budget in the last 30 days".

* **Implementation:**  
  * Check the LiteLLM User Info object.  
  * **Fallback:** Return the spend attribute from the User object (Total Life Time Spend) and label it clearly in the UI.

### **7.2. Error Handling**

* If LiteLLM is down: Return HTTP 503\.  
* If User is unauthorized: Return HTTP 401\.  
* If limits are exceeded: Return HTTP 400\.

## **8\. Development & Infrastructure**

### **8.1. LiteLLM Configuration**

* **Models:** A litellm\_config.yaml must be provided.  
* **Mockup Models:** For testing and development, include a model named fake-gpt-test that uses a mock provider (e.g., returning static responses) to allow budget increment testing without real costs.

### **8.2. Testing Strategy**

* **Tool:** pytest  
* **Coverage Requirement:** Minimum 75% code coverage.  
* **Integration Tests:**  
  * Spin up the LiteLLM container with the fake-gpt-test model.  
  * Generate a key via the App API.  
  * Use the generated key to call the LiteLLM fake-gpt-test endpoint.  
  * Verify spend increases in the App Dashboard (GET /api/me).

### **8.3. CI/CD Pipeline**

* **Platform:** GitHub Actions.  
* **Triggers:**  
  * **Pull Requests:** Run Linting (Ruff/Black) and Tests (Pytest with Coverage).  
  * **Main Push:** Build Docker Image and Push to Registry (if applicable), followed by deployment steps.  
* **Workflow:**  
  1. Checkout Code.  
  2. Set up Python & Dependencies.  
  3. Spin up LiteLLM Service container (using docker compose or service definition).  
  4. Run Pytest.  
  5. Check Coverage Report (fail if \< 75%).