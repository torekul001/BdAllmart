from db import fetch_all, fetch_one, get_connection

ISSUE_DEPARTMENTS = {
    "Product information": "Sales",
    "Order status": "Order",
    "Payment issue": "Accounts",
    "Return/refund": "Returns",
    "Technical support": "Technical",
    "Talk to agent": "Support",
}


def _clean(value, default=""):
    return str(value or default).strip()


def _priority_for_issue(issue_type, question):
    text = "{0} {1}".format(issue_type or "", question or "").lower()
    if any(word in text for word in ["urgent", "emergency", "payment failed", "paid", "refund", "cancel"]):
        return "Urgent"
    if any(word in text for word in ["payment", "return", "refund", "not received", "delivery"]):
        return "High"
    if any(word in text for word in ["order", "technical", "login", "problem"]):
        return "Medium"
    return "Low"


def _department_for_issue(issue_type):
    return ISSUE_DEPARTMENTS.get(_clean(issue_type), "Support")


def _add_column_if_missing(cursor, table, column, definition):
    safe_table = str(table).replace("'", "''")
    safe_column = str(column).replace("'", "''")
    cursor.execute(
        """
        IF COL_LENGTH('{0}', '{1}') IS NULL
        ALTER TABLE {2} ADD {3} {4}
        """.format(safe_table, safe_column, table, column, definition)
    )


def ensure_support_chat_tables():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            IF OBJECT_ID('dbo.SupportChatRequests', 'U') IS NULL
            CREATE TABLE dbo.SupportChatRequests (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                CustomerName NVARCHAR(150) NULL,
                ContactNo NVARCHAR(50) NOT NULL,
                Address NVARCHAR(500) NOT NULL,
                Question NVARCHAR(MAX) NULL,
                Status NVARCHAR(30) NOT NULL DEFAULT 'Open',
                AssignedTo NVARCHAR(100) NULL,
                CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
                UpdatedAt DATETIME NOT NULL DEFAULT GETDATE()
            )
            """
        )
        for column, definition in [
            ("IssueType", "NVARCHAR(80) NULL"),
            ("Email", "NVARCHAR(150) NULL"),
            ("OrderId", "NVARCHAR(80) NULL"),
            ("AttachmentUrl", "NVARCHAR(500) NULL"),
            ("Priority", "NVARCHAR(30) NOT NULL DEFAULT 'Low'"),
            ("Department", "NVARCHAR(80) NOT NULL DEFAULT 'Support'"),
            ("EscalatedTo", "NVARCHAR(100) NULL"),
            ("ResolvedAt", "DATETIME NULL"),
            ("ClosedAt", "DATETIME NULL"),
            ("FeedbackRating", "INT NULL"),
            ("FeedbackComment", "NVARCHAR(500) NULL"),
        ]:
            _add_column_if_missing(cursor, "dbo.SupportChatRequests", column, definition)
        cursor.execute(
            """
            IF OBJECT_ID('dbo.SupportChatMessages', 'U') IS NULL
            CREATE TABLE dbo.SupportChatMessages (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                RequestId INT NOT NULL,
                SenderType NVARCHAR(30) NOT NULL,
                SenderName NVARCHAR(150) NULL,
                Message NVARCHAR(MAX) NOT NULL,
                CreatedAt DATETIME NOT NULL DEFAULT GETDATE()
            )
            """
        )


def create_support_request(
    name,
    contact_no,
    address,
    question,
    issue_type="Talk to agent",
    email="",
    order_id="",
    attachment_url="",
):
    ensure_support_chat_tables()
    contact_no = _clean(contact_no)
    address = _clean(address)
    question = _clean(question)
    issue_type = _clean(issue_type, "Talk to agent")
    priority = _priority_for_issue(issue_type, question)
    department = _department_for_issue(issue_type)
    if not contact_no:
        raise ValueError("Contact number is required.")
    if not address:
        raise ValueError("Address is required.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.SupportChatRequests (
                CustomerName, ContactNo, Address, Question, IssueType,
                Email, OrderId, AttachmentUrl, Priority, Department
            )
            OUTPUT INSERTED.Id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                _clean(name),
                contact_no,
                address,
                question,
                issue_type,
                _clean(email),
                _clean(order_id),
                _clean(attachment_url),
                priority,
                department,
            ],
        )
        request_id = cursor.fetchone()[0]
        if question:
            cursor.execute(
                """
                INSERT INTO dbo.SupportChatMessages (RequestId, SenderType, SenderName, Message)
                VALUES (?, 'Customer', ?, ?)
                """,
                [request_id, _clean(name) or contact_no, question],
            )
        return request_id


def get_support_requests(status="", contact_no="", issue_type="", priority="", department=""):
    ensure_support_chat_tables()
    clauses = []
    params = []
    if status:
        clauses.append("R.Status = ?")
        params.append(status)
    if contact_no:
        clauses.append("R.ContactNo LIKE ?")
        params.append("%{0}%".format(contact_no))
    if issue_type:
        clauses.append("R.IssueType = ?")
        params.append(issue_type)
    if priority:
        clauses.append("R.Priority = ?")
        params.append(priority)
    if department:
        clauses.append("R.Department = ?")
        params.append(department)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return fetch_all(
        """
        SELECT
            R.Id,
            R.CustomerName,
            R.ContactNo,
            R.Address,
            R.Question,
            R.Status,
            R.AssignedTo,
            R.IssueType,
            R.Email,
            R.OrderId,
            R.AttachmentUrl,
            R.Priority,
            R.Department,
            R.EscalatedTo,
            R.ResolvedAt,
            R.FeedbackRating,
            R.CreatedAt,
            R.UpdatedAt,
            (SELECT COUNT(*) FROM dbo.SupportChatMessages M WHERE M.RequestId = R.Id) AS MessageCount
        FROM dbo.SupportChatRequests R
        {0}
        ORDER BY R.UpdatedAt DESC, R.Id DESC
        """.format(where),
        params,
    )


def get_support_request(request_id):
    ensure_support_chat_tables()
    return fetch_one("SELECT * FROM dbo.SupportChatRequests WHERE Id = ?", [request_id])


def get_support_messages(request_id):
    ensure_support_chat_tables()
    return fetch_all(
        """
        SELECT Id, RequestId, SenderType, SenderName, Message, CreatedAt
        FROM dbo.SupportChatMessages
        WHERE RequestId = ?
        ORDER BY Id ASC
        """,
        [request_id],
    )


def add_support_reply(request_id, sender_name, message, status="Answered"):
    ensure_support_chat_tables()
    message = str(message or "").strip()
    if not message:
        raise ValueError("Reply message is required.")
    status = str(status or "Answered").strip()
    resolved_clause = ", ResolvedAt = GETDATE()" if status in {"Resolved", "Closed"} else ""
    closed_clause = ", ClosedAt = GETDATE()" if status == "Closed" else ""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.SupportChatMessages (RequestId, SenderType, SenderName, Message)
            VALUES (?, 'Representative', ?, ?)
            """,
            [request_id, str(sender_name or "").strip(), message],
        )
        cursor.execute(
            """
            UPDATE dbo.SupportChatRequests
            SET Status = ?, AssignedTo = ?, UpdatedAt = GETDATE(){0}{1}
            WHERE Id = ?
            """.format(resolved_clause, closed_clause),
            [status, str(sender_name or "").strip(), request_id],
        )


def add_customer_message(request_id, sender_name, message):
    ensure_support_chat_tables()
    message = str(message or "").strip()
    if not message:
        raise ValueError("Message is required.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.SupportChatMessages (RequestId, SenderType, SenderName, Message)
            VALUES (?, 'Customer', ?, ?)
            """,
            [request_id, str(sender_name or "").strip(), message],
        )
        cursor.execute(
            """
            UPDATE dbo.SupportChatRequests
            SET Status = 'Open', UpdatedAt = GETDATE()
            WHERE Id = ?
            """,
            [request_id],
        )


def update_support_assignment(request_id, assigned_to="", status="", priority="", department="", escalated_to=""):
    ensure_support_chat_tables()
    updates = []
    params = []
    if assigned_to:
        updates.append("AssignedTo = ?")
        params.append(_clean(assigned_to))
    if status:
        updates.append("Status = ?")
        params.append(_clean(status))
        if status in {"Resolved", "Closed"}:
            updates.append("ResolvedAt = GETDATE()")
        if status == "Closed":
            updates.append("ClosedAt = GETDATE()")
    if priority:
        updates.append("Priority = ?")
        params.append(_clean(priority))
    if department:
        updates.append("Department = ?")
        params.append(_clean(department))
    if escalated_to:
        updates.append("EscalatedTo = ?")
        params.append(_clean(escalated_to))
        if not status:
            updates.append("Status = 'Escalated'")
    if not updates:
        return 0
    updates.append("UpdatedAt = GETDATE()")
    params.append(request_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dbo.SupportChatRequests SET {0} WHERE Id = ?".format(", ".join(updates)),
            params,
        )
        return cursor.rowcount


def save_support_feedback(request_id, rating, comment=""):
    ensure_support_chat_tables()
    try:
        rating_value = int(rating)
    except Exception:
        rating_value = 0
    if rating_value < 1 or rating_value > 5:
        raise ValueError("Rating must be between 1 and 5.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE dbo.SupportChatRequests
            SET FeedbackRating = ?, FeedbackComment = ?, Status = 'Closed',
                ClosedAt = GETDATE(), UpdatedAt = GETDATE()
            WHERE Id = ?
            """,
            [rating_value, _clean(comment), request_id],
        )
        cursor.execute(
            """
            INSERT INTO dbo.SupportChatMessages (RequestId, SenderType, SenderName, Message)
            VALUES (?, 'Customer', 'Feedback', ?)
            """,
            [request_id, "Rating: {0}/5. {1}".format(rating_value, _clean(comment))],
        )
