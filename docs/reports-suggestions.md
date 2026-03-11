# Reports Page – Suggested Reports & Charts

Use this list to choose which reports and charts to add to the **Reports** (Analytics) page. Each suggestion notes the **data source** so you can prioritize by effort.

**Already on Reports:** Overview (clients, projects, revenue, outstanding), Tasks by status (pie), Counts bar chart.

---

## 1. Finance

| Suggestion                             | Chart type                  | Description                                                          | Data source                                           |
| -------------------------------------- | --------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------- |
| **Revenue vs expenses (this month)**   | Bar or grouped bar          | Compare `revenue_this_month` and `expenses_this_month` from overview | Existing: `getOverview()`                             |
| **Revenue vs outstanding**             | Horizontal bar or KPI cards | Revenue collected vs outstanding invoices                            | Existing: `getOverview()`                             |
| **Revenue over time**                  | Line or area                | Monthly revenue (paid) trend                                         | New backend: time-series by month                     |
| **Expenses over time**                 | Line or area                | Monthly expenses trend                                               | New backend: time-series by month                     |
| **Invoices by status**                 | Pie or donut                | Draft / Sent / Paid / Overdue counts                                 | `listInvoices()` + client-side group by status        |
| **Top clients by revenue**             | Horizontal bar or table     | Clients ranked by total paid amount                                  | New backend or `listInvoices()` + group by client     |
| **Profit margin (revenue − expenses)** | KPI card or gauge           | Single number or simple gauge                                        | Existing: `revenue_this_month`, `expenses_this_month` |

---

## 2. Leads & pipeline

| Suggestion               | Chart type             | Description                                      | Data source                                                                 |
| ------------------------ | ---------------------- | ------------------------------------------------ | --------------------------------------------------------------------------- |
| **Leads by status**      | Pie / donut / bar      | New, Contacted, Qualified, Converted, Lost, etc. | Existing: `getDashboard().leads_by_status`                                  |
| **Conversion over time** | Line chart             | Leads converted to clients per month             | Existing: `getDashboard().conversion_over_time`                             |
| **Conversion rate**      | KPI card or big number | % of leads that became clients                   | Existing: `getDashboard().conversion_rate`                                  |
| **Leads this period**    | KPI cards              | Today / this week / this month                   | Existing: `getDashboard()` (leads_today, leads_this_week, leads_this_month) |
| **Leads by source**      | Pie or bar             | Where leads came from (e.g. website, referral)   | `listLeads()` + group by `source` (or new backend)                          |

---

## 3. Projects

| Suggestion                     | Chart type               | Description                                  | Data source                                              |
| ------------------------------ | ------------------------ | -------------------------------------------- | -------------------------------------------------------- |
| **Projects by stage**          | Horizontal bar or funnel | Lead, Discovery, Proposal, Development, etc. | Existing: `getDashboard().projects_by_stage`             |
| **Active vs total projects**   | KPI cards or small pie   | Active projects vs completed/archived        | Existing: `getOverview()` + optional backend for “total” |
| **Projects created over time** | Line or bar              | New projects per month                       | New backend or `listProjects()` + group by month         |
| **Projects by client**         | Bar or table             | Number of projects per client                | `listProjects()` + group by client_id                    |

---

## 4. Tasks

| Suggestion                     | Chart type              | Description                                      | Data source                                        |
| ------------------------------ | ----------------------- | ------------------------------------------------ | -------------------------------------------------- |
| **Tasks by status (enhanced)** | Donut with center total | Same as current pie but with total in center     | Existing: `getOverview()`                          |
| **Tasks over time**            | Line or stacked area    | Todo / In progress / Done trend by week or month | New backend: task counts over time                 |
| **Tasks by assignee**          | Horizontal bar or table | Task count per user                              | `listTasks()` + group by assignee (or new backend) |
| **Tasks by project**           | Bar or table            | Task count per project                           | `listTasks()` + group by project_id                |
| **Completion rate**            | KPI or gauge            | % of tasks done (e.g. done / total)              | Existing: `getOverview()` (tasks_done vs total)    |

---

## 5. Team & activity

| Suggestion             | Chart type   | Description                       | Data source                                           |
| ---------------------- | ------------ | --------------------------------- | ----------------------------------------------------- |
| **Total users**        | KPI card     | Headcount                         | Existing: `getOverview().total_users`                 |
| **Activity over time** | Line or bar  | Team activity events per day/week | New backend or `listTeamActivity()` + group by date   |
| **Activity by user**   | Bar or table | Who is most active                | `listTeamActivity()` + group by user (or new backend) |
| **Activity by type**   | Pie or bar   | Logins, updates, creates, etc.    | `listTeamActivity()` + group by action/type           |

---

## 6. Meetings (if you add meeting stats later)

| Suggestion              | Chart type | Description                        | Data source                                       |
| ----------------------- | ---------- | ---------------------------------- | ------------------------------------------------- |
| **Meetings this month** | KPI card   | Count of meetings in current month | New backend or `listMeetings()` + filter by month |
| **Meetings by project** | Bar        | Meetings per project               | `listMeetings()` + group by project               |

---

## 7. Cross-cutting / summary

| Suggestion            | Chart type       | Description                                                        | Data source                                 |
| --------------------- | ---------------- | ------------------------------------------------------------------ | ------------------------------------------- |
| **Executive summary** | Row of KPI cards | Revenue, outstanding, active projects, tasks done, conversion rate | Mix of `getOverview()` and `getDashboard()` |
| **Period selector**   | Filter UI        | “This month” / “Last 3 months” / “This year” for time-based charts | Frontend only; backend may need date params |
| **Export to PDF/CSV** | Button           | Download current report or table as PDF or CSV                     | Frontend + optional backend                 |

---

## Quick wins (existing API only)

- **Revenue vs expenses this month** – bar chart from `getOverview()`.
- **Leads by status** – pie/donut from `getDashboard().leads_by_status`.
- **Conversion over time** – line chart from `getDashboard().conversion_over_time`.
- **Conversion rate** – single KPI from `getDashboard().conversion_rate`.
- **Projects by stage** – bar from `getDashboard().projects_by_stage`.
- **Leads today / week / month** – three KPI cards from `getDashboard()`.
- **Total users** – KPI from `getOverview().total_users`.
- **Profit this month** – revenue_this_month − expenses_this_month from `getOverview()`.

---

## Data source legend

- **Existing** – Data already returned by `getOverview()` or `getDashboard()`; only frontend work.
- **List APIs** – Use existing list endpoints and aggregate in the frontend (may need pagination or higher limits).
- **New backend** – Requires a new or extended analytics/API endpoint (e.g. time-series, aggregates by month/user).

After you select which items to implement, we can add them to the Reports page in order of priority.
