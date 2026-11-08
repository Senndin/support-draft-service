# Example: collecting evidence in a Django project

An illustration of what the boundary evidence of step 3 looks like in one specific project. It is not a rule for every project -- the layers and the commands are whatever the project actually has.

The path here is `view -> service -> ORM -> MySQL`.

## Reading the traceback

Most frames belong to the framework.
Read upward to the innermost frame whose file lives in the project -- that is where the project's own code produced or passed the bad value.

## Recording the boundaries

Instrument every layer first, then run the failing path once.

| Boundary | What to record | How |
|---|---|---|
| client -> view | what Django actually parsed from the request | log `request.GET` and `request.POST` at the top of the view |
| view -> service | the arguments the view assembled | log them immediately before the service call |
| service -> ORM | the queryset before it is evaluated | `print(qs.query)` -- it shows the SQL without touching the database |
| ORM -> database | the SQL sent, and how many rows came back | the `django.db.backends` logger at `DEBUG` |

One instrumented run says which boundary the value went bad at.
Investigate that component, and leave the others alone until it is ruled out.

## Narrowing further

`uv run python manage.py shell` calls a service without the client, the middleware or the view.
If it fails there too, the request handling is ruled out.

For a failing test, `uv run poe test:unit <target> --pdb` stops at the failure with the local variables intact.
