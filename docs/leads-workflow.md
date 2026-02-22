# Leads Workflow: From Lead to Project and Meetings

This document explains how leads work end-to-end: visibility, conversion, management assignment, and meetings with notifications.

---

## 1. Lead lifecycle and visibility

### New leads (status = "new")
- **Visible to:** All users with the **sales** role (and admins).
- **Purpose:** Any sales team member can see and work on new leads (e.g. contact, qualify).
- **Assignment:** No assignee yet; anyone in sales can pick them up.

### Once the lead leaves "new"
- When status changes to **contacted**, **qualified**, **converted**, **lost**, **closed**, or **dead**:
  - **Visible to:** Only the **assigned member** (who moved it out of "new" or was assigned), their **manager**, and **admins**.
- **Assigned to** is set automatically when a user changes the lead’s status from "new" to something else.
- **Converted or closed:** When the lead is in **converted** or **closed** stage, **only management** (manager or admin) can edit or delete it. Simple members cannot change the lead anymore.

---

## 2. Converting a lead (two steps)

### Step 1: Member marks the lead as converted
- **Who:** The **sales member** (assignee) working on the lead.
- **Action:** They click **"Mark as converted"**. This only updates the lead **status** to `"converted"`. No client or project is created.
- **Effect:** The lead appears to **management** (managers and admins), who can then create the client and project.

### Step 2: Management creates client and project
- **Who:** Only **management** (users with direct reports or admin) can create the client and project from a lead.
- **Action:** They click **"Create client & project"** on a lead that is marked converted (status = "converted") and not yet linked to a client.
- **What happens:**
  1. A **Client** is created from the lead (company name, contact, etc.).
  2. Optionally a **Project** is created and linked to that client.
  3. The lead is linked to the new client (`converted_to_client_id`, `converted_at`).

- **Convert dialog lets management:**
  - Choose **client team** (which team owns the client).
  - Choose whether to **create a project** and set project name, pipeline stage, assigned team.
  - The user performing the action is set as the project **owner** (project manager) by default.

So **members** only mark the lead as converted; **management** creates the client and project and assigns project manager and team.

---

## 3. After conversion: management and project setup

- **Who sees the new client and project:** Depends on your existing scoping:
  - **Admins** see everything.
  - **Managers** see clients/projects where they or their reports are involved (e.g. `created_by` or `owner_id` in their scope).
  - **Team members** see by team (e.g. `assigned_team_id` / client’s team).

So **“shows to management”** means:
- Managers (and admins) see the new client and project in **Clients** and **Projects**.
- They can **assign a project manager** by editing the project and setting **Owner** (`owner_id`).
- They can **assign the team** by setting **Assigned team** (`assigned_team_id`) on the project.
- They can create the project at convert time (as above) or create additional projects later from the Clients/Projects area.

**Where to do it in the app:**
- **Projects** list/detail → Edit project → set **Owner** (project manager) and **Assigned team**.
- Permissions: only users who can edit that project (e.g. admin or manager in scope) can change owner and team.

---

## 4. Meetings while working on the lead/project

- **When:** After a project exists (e.g. from a converted lead), users who can access that project can create **meetings** for it.
- **Meetings** can be linked to a **project** (`project_id`) and have:
  - Title, description, start/end time, location
  - **Attendees:** a list of users (**assigned users**) selected for that meeting.

- **How assigning works:**
  - When creating or editing a meeting, the user selects **which users** to assign (attendees).
  - Those users are stored as **meeting attendees** (`MeetingAttendee`: meeting_id + user_id).
  - **Assigned users receive a notification** for the meeting (see below).

- **Who can create/edit meetings:** Users with `meetings:write` who can access the project (e.g. project owner, team members, manager, admin).
- **Who can see the meeting:** Creator, attendees, and (depending on rules) managers/admins.

So: **while working on the lead (or the resulting project), you assign meetings to the users you want; those users get a notification.**

---

## 5. Notifications for meeting attendees

- When a **meeting is created** or **updated** with a list of attendees:
  - The system creates a **Notification** for **each attendee** (each assigned user).
- Each notification has:
  - **Title** (e.g. “Meeting: &lt;title&gt;”)
  - **Message** (e.g. time and project)
  - **Link** to the meeting (e.g. `/meetings/{id}`) so the user can open it.
  - **Type** `meeting` so the UI can treat it as a meeting invite.
- Users see these in the **Notifications** area and can mark them as read.

So **assigned users get a notification for the meeting** and can open it from the notification.

---

## 6. End-to-end flow (summary)

1. **Lead is generated** → Visible to all **sales**; anyone can work on it.
2. **Lead is worked on** → Status moves to contacted/qualified; **assigned to** is set; only assignee, manager, and admin see it.
3. **Member marks as converted** → Member clicks **"Mark as converted"**; only status is set to "converted". Lead is now visible to management; **member can no longer edit** it (converted/closed are locked for members).
4. **Management creates client & project** → Manager or admin clicks **"Create client & project"**; **Client** and optional **Project** are created; **project manager (owner)** and **assigned team** are set.
5. **Management** can **assign/change project manager** and **assign team** via project edit.
6. **While working** (on lead or project) → Users create **meetings**, **select attendees**; **attendees get a notification** for the meeting.
7. **Ongoing work** → Tasks, meetings, and project updates continue on the project; managers and assignees stay in the loop via visibility and notifications.

---

## 7. Relevant API and data

| Area            | API / model              | Notes                                                                 |
|-----------------|--------------------------|-----------------------------------------------------------------------|
| Leads           | `GET/POST/PATCH /api/v1/leads`, `POST .../convert` | Visibility by status and assignee; convert creates client + project.  |
| Clients         | `GET/POST/PATCH /api/v1/clients`                   | Created from lead; have `team_id`.                                    |
| Projects        | `GET/POST/PATCH /api/v1/projects`                  | `owner_id` = project manager; `assigned_team_id` = team.              |
| Meetings        | `GET/POST/PATCH /api/v1/meetings`                  | `project_id`, `attendee_ids`; notifications created for attendees.  |
| Notifications   | `GET /api/v1/notifications`                        | User’s notifications (including meeting type with link).              |

This is how leads work once a lead is converted, how it shows to management for assigning a project manager and team, how the project is created and used, and how meetings and their assigned users get notifications.
