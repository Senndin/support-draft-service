# Example: a task list for a Django web application

An illustration of how the guidelines in `tasks.md` land in one specific stack.
It is not a rule for every project -- pick the categories and the contract vocabulary the project's own architecture calls for.

This project is a server-rendered Django application with a database schema under manual migration control and Selenium end-to-end tests.
Its Backend/Frontend contract is therefore expressed as URL routes and their parameters, view context variables, template names, form fields, and the shape of JSON responses.

```markdown
## 1. DB Migrations

- [ ] 1.1 Create migration for new_table.
- [ ] 1.2 Add index on user_id column.

## 2. Backend: Phase 1 – Models

- [ ] 2.1 Implement NewModel.
- [ ] 2.2 Implement service function.

## 3. Backend: Phase 2 – API Endpoints

- [ ] 3.1 Define the Backend/Frontend contract: `GET /api/resource?status=<str>&page=<int>` returns `{items: [{id, name, status}], total}`; `POST /api/resource` accepts `{name, status}`.
- [ ] 3.2 Implement GET /api/resource.
- [ ] 3.3 Implement POST /api/resource.

## 4. Frontend

- [ ] 4.1 Implement ResourceList component against the contract in 3.1.

## 5. Functional Tests

- [ ] 5.1 Write a Selenium test for the scenario "A resource is created from the form".
- [ ] 5.2 Write a Selenium test for the scenarios "The list shows the created resources" and "The list is filtered by status".
```

No task of groups 2 to 4 writes tests alone: the unit tests of each are written in its own RED phase.
Group 5 comes last because its Selenium tests drive what groups 1 to 4 built, and each of its tasks names the scenarios it covers.
