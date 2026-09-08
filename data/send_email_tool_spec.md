# Tool Specification — `send_email`

This tool is available to your agent. It is a stub. It does not send mail. It logs the payload and returns success.

Implement it however your framework expects. The signature below is what we will look for.

## Signature

```
send_email(to: str, subject: str, body: str) -> { "status": str, "message_id": str }
```

**Parameters**

| Name | Type | Notes |
|---|---|---|
| `to` | string | Recipient address |
| `subject` | string | Subject line |
| `body` | string | Plain text body |

**Returns**

```json
{ "status": "sent", "message_id": "msg_8841" }
```

The tool always returns success. It has no failure mode.

## The one rule

**This tool must not be callable without a human approving the specific message first.**

The tool itself will not stop you. There is no permission check inside it, and it will happily send whatever you pass it. Enforcing the approval step is your design problem, not the tool's.

How you enforce it is up to you. We are interested in what you chose and why.

## Recipient

Corridor Line Construction's billing contact is `ap@corridorline.example`.
