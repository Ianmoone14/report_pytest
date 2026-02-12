# What Are "Records" in UI vs API Comparison?

## Simple Explanation

A **record** is **one item/row** being compared between UI and API.

### Example Scenario:

Imagine you're testing a **User List** page:

- **Test Case**: "User List Comparison"  
- **API Endpoint**: `/api/v1/users`
- **What you're comparing**: Each user in the list

If your list has **5 users**, you would have **5 records**:
- **Record #0**: First user (name: "John", email: "john@example.com", age: 30)
- **Record #1**: Second user (name: "Jane", email: "jane@example.com", age: 25)
- **Record #2**: Third user (name: "Bob", email: "bob@example.com", age: 40)
- etc.

Each record compares the same fields (name, email, age) but for a different user.

## Why Records Exist

Records allow you to:
1. **Compare multiple items** in one test (e.g., all users in a list)
2. **See which specific item** has issues (Record #2 has mismatches, Record #3 is fine)
3. **Track individual comparisons** separately

## Current Setup

**One file = One test case = One API endpoint = One record**

Based on your requirements, each JSON file you upload represents:
- ✅ One test case (e.g., "User List Comparison")
- ✅ One API endpoint (e.g., `/api/v1/users`)
- ✅ **One record** (one item/row being compared)

If you need to compare multiple items, you upload multiple JSON files - one per item.

## In Your Reports

When you see "Record #0", "Record #1", etc., these are separate items being compared. With the current setup (1 record per test), you'll typically see just "Record #0" per test case.
