# What are "Records" in UI vs API Comparison?

## Understanding Records

A **record** is one row/item being compared between UI and API.

### Example:
- **Test Case**: "User List Comparison"
- **API Endpoint**: `/api/v1/users`
- **Records**: Each user in the list is a separate record

If you have 5 users in your list, you would have 5 records:
- Record #0: First user (name, email, age, status)
- Record #1: Second user (name, email, age, status)
- Record #2: Third user (name, email, age, status)
- etc.

## Current Setup

**One file = One test case = One API endpoint = One record**

Each JSON file you upload represents:
- One test case (e.g., "User List Comparison")
- One API endpoint (e.g., `/api/v1/users`)
- One record comparison (one row/item being compared)

If you need to compare multiple records, upload multiple JSON files - one per record.

## Why This Design?

This allows you to:
1. Upload test results incrementally
2. Track each comparison separately
3. See which specific record has issues
4. Add more test cases to a run over time
