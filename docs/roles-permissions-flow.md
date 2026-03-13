# Software House Management System

## Roles, Permissions, and Page Access Flow

## 1. System Overview

The Software House Management System is designed to manage internal operations of a software company including:

* Leads management
* Client management
* Project tracking
* Task management
* Meetings scheduling
* Messaging system
* Financial management
* Team management
* Reporting and analytics

The system uses **Role-Based Access Control (RBAC)** combined with **Team-Based Access** to ensure users only see information relevant to their responsibilities.

There are **three primary roles** in the system:

1. Admin
2. Manager
3. Employee

Each role has different access permissions to system modules and data.

---

## 2. Role Hierarchy

### 2.1 Admin

Admins represent executive leadership and system administrators.

Examples:

* CEO
* CTO
* CFO
* HR Head
* System Administrator

**Responsibilities**

* Full system management
* Manage users and teams
* View company-wide analytics
* Manage finances and reports
* Configure system roles and permissions

**Access Level**

Full access to all modules and data across the company.

---

### 2.2 Manager

Managers are responsible for **specific teams or departments**.

Examples:

* Project Manager
* Team Lead
* Sales Manager
* Engineering Manager

**Responsibilities**

* Manage team members
* Create and manage projects
* Assign tasks to team members
* Manage meetings
* Track team performance
* Manage clients related to their team

**Access Level**

Managers can access **data related only to their assigned team**.

---

### 2.3 Employee

Employees are team members who execute tasks assigned to them.

Examples:

* Developers
* Designers
* QA Engineers
* Sales Executives
* Support Engineers

**Responsibilities**

* Work on assigned tasks
* Participate in meetings
* Communicate with team members
* Update task progress

**Access Level**

Employees can only access **their assigned tasks, projects, and messages**.

Employees **cannot access management or financial data**.

---

## 3. Team Structure

Users belong to specific teams.

Example teams in a software house:

* Frontend Team
* Backend Team
* DevOps Team
* QA Team
* Sales Team
* Marketing Team
* HR Team
* Finance Team

Each team has:

* **1 Manager**
* **Multiple Employees**

Example structure:

**Frontend Team**
* Manager → Frontend Lead
* Employees → React Developers

**Backend Team**
* Manager → Backend Lead
* Employees → API Developers

---

## 4. System Pages

The system includes the following modules:

* Overview
* Leads
* Clients
* Projects
* Tasks
* Meetings
* Messages
* Invoices
* Expenses
* Reports
* Team Activity
* Announcements
* Users
* Teams
* Roles

Access to these modules is controlled by user role.

---

## 5. Page Access Control

| Page          | Admin            | Manager            | Employee           |
| ------------- | ---------------- | ------------------ | ------------------ |
| Overview      | Full analytics   | Team analytics     | Personal analytics |
| Leads         | Full access      | Team leads         | Limited (optional) |
| Clients       | Full access      | Team clients       | No access          |
| Projects      | All projects     | Team projects      | Assigned projects  |
| Tasks         | All tasks        | Team tasks         | Assigned tasks    |
| Meetings      | All meetings     | Team meetings      | Invited meetings  |
| Messages      | Full messaging   | Team messaging     | Team messaging    |
| Invoices      | Full access      | View team invoices | No access         |
| Expenses      | Full access      | No access          | No access         |
| Reports       | All reports      | Team reports       | No access         |
| Team Activity | All teams        | Team only          | No access         |
| Announcements | Create/Edit/View | View               | View              |
| Users         | Manage users     | No access          | No access         |
| Teams         | Manage teams     | No access          | No access         |
| Roles         | Manage roles     | No access          | No access         |

---

## 6. Overview Page Analytics

The **Overview Dashboard** shows different analytics depending on the user role.

### Admin Overview

Admins can see **company-wide analytics**, including:

* Total leads
* Total clients
* Active projects
* Completed projects
* Total revenue
* Company expenses
* Team performance
* Employee productivity
* Financial reports

---

### Manager Overview

Managers see **analytics related to their team only**.

Examples:

* Team projects
* Tasks completed by team
* Team productivity
* Team meetings
* Team leads
* Team clients
* Project progress

Managers **cannot view financial data like company expenses**.

---

### Employee Overview

Employees see **only personal work data**.

Examples:

* Assigned tasks
* Task completion progress
* Upcoming meetings
* Personal productivity
* Messages
* Announcements

Employees **cannot view company analytics or financial data**.

---

## 7. Financial Access Rules

Financial information is restricted.

### Invoices

| Role     | Access                |
| -------- | --------------------- |
| Admin    | Full access           |
| Manager  | View related invoices |
| Employee | No access             |

---

### Expenses

Expenses are **highly restricted**.

| Role     | Access      |
| -------- | ----------- |
| Admin    | Full access |
| Manager  | No access   |
| Employee | No access   |

This ensures financial privacy and security.

---

## 8. Project and Task Visibility

Projects and tasks are filtered by **team assignment**.

**Managers can see:**
* Projects assigned to their team
* Tasks assigned to team members

**Employees can see:**
* Projects they are assigned to
* Tasks assigned to them

Example logic:

* Manager: `show projects where project.team_id = user.team_id` (or owner in manager scope)
* Employee: `show tasks where task.assignee_id = user.id`

---

## 9. Client Visibility

Client data is restricted to protect business relationships.

| Role     | Access       |
| -------- | ----------- |
| Admin    | Full access  |
| Manager  | Team clients |
| Employee | No access    |

Employees **cannot see client information**.

---

## 10. Messaging System

Messaging allows communication between team members.

**Roles allowed:** Admin, Manager, Employee

**Messaging features:**
* Direct messaging
* Team channels
* Project discussion threads

---

## 11. Announcements

Announcements are used for **company updates**.

Example announcements:
* Holiday notice
* Company meeting
* Policy changes

| Role     | Permissions        |
| -------- | ------------------ |
| Admin    | Create/Edit/Delete |
| Manager  | View               |
| Employee | View               |

---

## 12. Team Activity

Team activity shows actions such as:
* Task updates
* Project changes
* Team member actions

**Access rules:**
* Admin → All teams
* Manager → Their team
* Employee → No access

---

## 13. User Management

User management is restricted.

**Admin can:**
* Create users
* Assign roles
* Assign teams
* Disable accounts

Managers and Employees **cannot access user management**.

---

## 14. Role and Permission Management

Only Admin can:
* Create roles
* Assign permissions
* Modify role access

This ensures security and prevents unauthorized changes.

---

## 15. Security Principles

The system follows these security principles:

### Role Based Access Control
Users only access modules allowed by their role.

### Team Based Filtering
Users see only data related to their team.

### Data Privacy
Sensitive data such as:
* Expenses
* Financial reports
* Clients

is restricted to authorized roles.

---

## 16. Example System Flow

Example workflow:

1. Admin creates teams
2. Admin creates users
3. Admin assigns roles and teams
4. Managers create projects
5. Managers assign tasks to employees
6. Employees update task progress
7. Managers track team performance
8. Admin monitors overall company performance
