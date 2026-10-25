# Test a template

Render it against live state before putting it in a file:

```
curl -s -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template": "{{ states(\"sun.sun\") }}"}' \
  http://supervisor/core/api/template
```

The reply is the rendered text. An error message comes back as text too: read
it, fix the template, render again, then put it in a file.
