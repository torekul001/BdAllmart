from urllib.parse import parse_qs, urlparse
from datetime import datetime

from db import execute, fetch_all, fetch_one
from security import password_for_storage
from course_content import sanitize_course_content, video_code


DEFAULT_COURSES = [
    "Web Design",
    "Logo Design",
    "Graphic Design",
    "Image Editing",
    "Mobile Apps",
    "Software Develop",
    "Java Application",
    "Data Entry",
    "Email Marketing",
    "Seach Engine Optimaization(SEO)",
]


def clean_text(value, limit=50):
    return str(value or "").strip()[:limit]


def table_exists(table_name):
    row = fetch_one(
        """
        SELECT COUNT(1) AS Total
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = ?
        """,
        [table_name],
    )
    return bool(row and int(row.get("Total") or 0) > 0)


def ensure_course_category_column():
    row = fetch_one(
        """
        SELECT COUNT(1) AS Total
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'ClassVideo' AND COLUMN_NAME = 'CourseCategory'
        """
    )
    if row and int(row.get("Total") or 0) > 0:
        return

    execute("ALTER TABLE ClassVideo ADD CourseCategory nvarchar(50) NULL")
    migrate_existing_course_categories()


def migrate_existing_course_categories():
    categories = get_course_categories()
    for category in sorted(categories, key=len, reverse=True):
        execute(
            """
            UPDATE ClassVideo
            SET CourseCategory = ?
            WHERE ISNULL(CourseCategory, '') = ''
              AND (
                    Course = ?
                 OR Course LIKE ? + ' %'
                 OR Course LIKE ? + '%'
              )
            """,
            [category, category, category, category],
        )
    execute(
        """
        UPDATE ClassVideo
        SET CourseCategory = 'Other'
        WHERE ISNULL(CourseCategory, '') = '' AND ISNULL(Course, '') <> ''
        """
    )


def youtube_id(value):
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.netloc:
        host = parsed.netloc.lower()
        if "youtu.be" in host:
            return parsed.path.strip("/").split("/")[0]
        if "youtube.com" in host:
            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/embed/", 1)[1].split("/")[0]
            query_video = parse_qs(parsed.query).get("v", [""])[0]
            if query_video:
                return query_video
    return text.split("&")[0].split("?")[0].strip()


def get_course_categories():
    try:
        rows = fetch_all("SELECT Services FROM ServicesType WHERE ISNULL(Services, '') <> '' ORDER BY Services")
        names = [row["Services"] for row in rows if row.get("Services")]
    except Exception:
        names = []

    try:
        row_categories = fetch_all(
            """
            SELECT DISTINCT CourseCategory
            FROM ClassVideo
            WHERE ISNULL(CourseCategory, '') <> ''
            ORDER BY CourseCategory
            """
        )
        names.extend(row["CourseCategory"] for row in row_categories if row.get("CourseCategory"))
    except Exception:
        pass

    merged = []
    source_names = names or DEFAULT_COURSES
    for name in source_names:
        value = clean_text(name)
        if value and value.lower() not in {item.lower() for item in merged}:
            merged.append(value)
    return merged


def get_course_names(category=None):
    ensure_course_category_column()
    params = []
    where = "WHERE ISNULL(Course, '') <> ''"
    if category:
        where += " AND CourseCategory = ?"
        params.append(category)

    names = []
    try:
        rows = fetch_all(
            f"""
            SELECT DISTINCT Course
            FROM ClassVideo
            {where}
            ORDER BY Course
            """,
            params,
        )
        names.extend(row["Course"] for row in rows if row.get("Course"))
    except Exception:
        pass

    merged = []
    for name in names:
        value = clean_text(name)
        if value and value.lower() not in {item.lower() for item in merged}:
            merged.append(value)
    return merged


def ensure_course_content_column():
    execute("IF COL_LENGTH('ClassVideo', 'ContentHtml') IS NULL ALTER TABLE ClassVideo ADD ContentHtml nvarchar(max) NULL")


def get_public_course_videos():
    ensure_course_category_column()
    ensure_course_content_column()
    return fetch_all("SELECT Id, CourseCategory, Course, Name, VideoLink, ContentHtml FROM ClassVideo ORDER BY CourseCategory, Id")


def get_public_course_video(video_id):
    ensure_course_category_column()
    ensure_course_content_column()
    return fetch_one("SELECT Id, CourseCategory, Course, Name, VideoLink, ContentHtml FROM ClassVideo WHERE Id = ?", [video_id])


def get_course_videos(course=None, category=None):
    ensure_course_category_column()
    params = []
    filters = []
    if course:
        filters.append("Course = ?")
        params.append(course)
    if category:
        filters.append("CourseCategory = ?")
        params.append(category)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    return fetch_all(
        f"""
        SELECT
            Id,
            CourseCategory,
            Course,
            Name,
            VideoLink
        FROM ClassVideo
        {where}
        ORDER BY Course, Id
        """,
        params,
    )


def get_course_video_groups(category=None):
    videos = get_course_videos(category=category)
    groups = []
    index_by_category = {}
    for video in videos:
        category_name = str(video.get("CourseCategory") or "Uncategorized").strip() or "Uncategorized"
        if category_name not in index_by_category:
            index_by_category[category_name] = {"category": category_name, "videos": []}
            groups.append(index_by_category[category_name])
        index_by_category[category_name]["videos"].append(video)
    return groups


def add_course_video(category, title, youtube_link, content_html="", video_id=None):
    ensure_course_category_column()
    ensure_course_content_column()
    code = video_code(youtube_link)
    if not category or not title:
        raise ValueError("Course category, lesson title, and YouTube link are required.")
    values = [clean_text(category), clean_text(category), clean_text(title), code, sanitize_course_content(content_html)]
    if video_id:
        execute("UPDATE ClassVideo SET CourseCategory = ?, Course = ?, Name = ?, VideoLink = ?, ContentHtml = ? WHERE Id = ?", values + [video_id])
        return
    execute(
        "INSERT INTO ClassVideo (CourseCategory, Course, Name, VideoLink, ContentHtml) VALUES (?, ?, ?, ?, ?)",
        values,
    )


def delete_course_video(video_id):
    execute("DELETE FROM ClassVideo WHERE Id = ?", [video_id])


def get_students():
    rows = fetch_all(
        """
        SELECT
            StdId,
            Name,
            MobileNo,
            Email,
            Course,
            Institute,
            Status,
            'StudentAdmision' AS SourceTable
        FROM StudentAdmision
        ORDER BY Name
        """
    )
    if table_exists("StudentAdmission"):
        rows.extend(
            fetch_all(
                """
                SELECT
                    studentid AS StdId,
                    name AS Name,
                    contactno AS MobileNo,
                    email AS Email,
                    coursename AS Course,
                    refId AS Institute,
                    '' AS Status,
                    'StudentAdmission' AS SourceTable
                FROM StudentAdmission
                ORDER BY name
                """
            )
        )
    seen = set()
    students = []
    for row in rows:
        std_id = str(row.get("StdId") or "").strip()
        if not std_id or std_id in seen:
            continue
        seen.add(std_id)
        students.append(row)
    return students


def get_student(std_id):
    student = fetch_one(
        """
        SELECT TOP 1
            StdId,
            Name,
            MobileNo,
            Email,
            Course,
            Institute,
            Status
        FROM StudentAdmision
        WHERE StdId = ?
        """,
        [std_id],
    )
    if student or not table_exists("StudentAdmission"):
        return student
    return fetch_one(
        """
        SELECT TOP 1
            studentid AS StdId,
            name AS Name,
            contactno AS MobileNo,
            email AS Email,
            coursename AS Course,
            refId AS Institute,
            '' AS Status
        FROM StudentAdmission
        WHERE studentid = ?
        """,
        [std_id],
    )


def get_student_for_user(username, phone="", email=""):
    student = fetch_one(
        """
        SELECT TOP 1
            StdId,
            Name,
            MobileNo,
            Email,
            Course,
            Institute,
            Status
        FROM StudentAdmision
        WHERE StdId = ? OR Name = ? OR MobileNo = ? OR Email = ?
        ORDER BY Id DESC
        """,
        [username, username, phone or "", email or ""],
    )
    if student or not table_exists("StudentAdmission"):
        return student
    return fetch_one(
        """
        SELECT TOP 1
            studentid AS StdId,
            name AS Name,
            contactno AS MobileNo,
            email AS Email,
            coursename AS Course,
            refId AS Institute,
            '' AS Status
        FROM StudentAdmission
        WHERE studentid = ? OR name = ? OR contactno = ? OR email = ?
        ORDER BY id DESC
        """,
        [username, username, phone or "", email or ""],
    )


def next_student_id():
    row = fetch_one("SELECT ISNULL(MAX(Id), 0) + 1 AS NextId FROM StudentAdmision")
    return "STU-{0}".format(row.get("NextId") if row else 1)


def find_user_by_contact(contact_no):
    return fetch_one(
        """
        SELECT TOP 1 UserId, Username, Phone, UserCatagory
        FROM Users
        WHERE Username = ? OR Phone = ?
        """,
        [contact_no, contact_no],
    )


def get_reference_users():
    return fetch_all(
        """
        SELECT TOP 500
            UserId,
            Username,
            FirstName,
            Phone,
            Email,
            UserCatagory
        FROM Users
        WHERE ISNULL(Username, '') <> ''
        ORDER BY Username
        """
    )


def create_student_login_account(name, mobile, email, address, reference):
    mobile = clean_text(mobile, 20)
    if not mobile:
        raise ValueError("Student mobile number is required for login account.")

    existing = find_user_by_contact(mobile)
    if existing:
        return existing, False

    execute(
        """
        INSERT INTO Users
            (Username, Password, Email, Active, Status, Phone, Code, FirstName, Address, UserCatagory, referance, Lavel, Reting)
        VALUES
            (?, ?, ?, 1, 'True', ?, ?, ?, ?, 'Designer', ?, ?, ?)
        """,
        [
            mobile,
            password_for_storage("123456"),
            clean_text(email, 150) or "{0}@allservicer.local".format(mobile),
            mobile,
            "00000",
            clean_text(name, 250),
            clean_text(address, 500),
            clean_text(reference, 150) or "2",
            "5",
            "3",
        ],
    )
    return find_user_by_contact(mobile), True


def enroll_student(name, mobile, email, address, course, fee, institute, reference):
    if not name or not mobile or not course:
        raise ValueError("Student name, mobile, and course are required.")
    if not reference:
        raise ValueError("Please select a reference user.")
    existing = fetch_one(
        """
        SELECT TOP 1 StdId
        FROM StudentAdmision
        WHERE MobileNo = ? AND Course = ?
        """,
        [mobile, course],
    )
    if existing:
        raise ValueError("This mobile number is already enrolled in this course.")

    std_id = next_student_id()
    user, user_created = create_student_login_account(name, mobile, email, address, reference)
    execute(
        """
        INSERT INTO StudentAdmision
            (StdId, Name, PresentAddress, Email, MobileNo, Course, CoursrFee, Institute, Date, Status)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            std_id,
            clean_text(name, 150),
            clean_text(address, 250),
            clean_text(email, 150),
            clean_text(mobile),
            clean_text(course),
            int(float(fee or 0)),
            clean_text(institute or "Admin", 250),
            datetime.now().strftime("%Y-%m-%d"),
            "Active",
        ],
    )
    return {
        "student_id": std_id,
        "username": clean_text(mobile, 20),
        "password": "123456",
        "user_id": (user or {}).get("UserId"),
        "user_created": user_created,
    }


def get_assigned_video_links(std_id):
    rows = fetch_all("SELECT videoLink FROM StudentVideo WHERE StdId = ?", [std_id])
    return {str(row.get("videoLink") or "").strip() for row in rows}


def assign_videos_to_student(std_id, course, video_ids):
    if not std_id:
        raise ValueError("Please select a student.")
    if not course:
        raise ValueError("Please select a course category.")
    if not video_ids:
        raise ValueError("Please select at least one lesson.")

    videos = get_course_videos(category=course)
    selected = [video for video in videos if str(video["Id"]) in {str(item) for item in video_ids}]
    assigned = get_assigned_video_links(std_id)
    added = 0

    for video in selected:
        video_link = str(video.get("VideoLink") or "").strip()
        if not video_link or video_link in assigned:
            continue
        execute(
            "INSERT INTO StudentVideo (Course, StdId, videoLink) VALUES (?, ?, ?)",
            [clean_text(course), clean_text(std_id), video_link[:50]],
        )
        assigned.add(video_link)
        added += 1
    return added


def get_student_assigned_videos(std_id):
    return fetch_all(
        """
        SELECT
            sv.Id AS AssignmentId,
            sv.Course,
            cv.CourseCategory,
            cv.Id AS VideoId,
            ISNULL(cv.Name, 'Class Video') AS Name,
            sv.videoLink AS VideoLink
        FROM StudentVideo sv
        LEFT JOIN ClassVideo cv
            ON cv.VideoLink = sv.videoLink
           AND (cv.Course = sv.Course OR cv.CourseCategory = sv.Course)
        WHERE sv.StdId = ?
        ORDER BY sv.Id DESC
        """,
        [std_id],
    )
