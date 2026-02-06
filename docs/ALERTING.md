# Alerting Guide - Alertmanager Setup

## Overview

Alertmanager handles alerts sent by Prometheus and routes them to the appropriate receivers (Slack, Email, PagerDuty).

**Features:**
- 📢 **Multi-channel notifications** (Slack, Email, PagerDuty)
- 🎯 **Smart routing** by severity and alert type
- 🔇 **Inhibition rules** (suppress redundant alerts)
- 📋 **Grouping** (batch similar alerts)
- 🔄 **Auto-resolution** notifications

---

## Quick Start

### 1. Configure Slack Webhook

Get your Slack webhook URL:
1. Go to https://api.slack.com/apps
2. Create new app → Incoming Webhooks
3. Activate webhooks → Add to channel
4. Copy webhook URL

Edit `alertmanager.yml`:
```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
```

### 2. Create Slack Channels

Recommended channels:
- `#genai-alerts` - All alerts (warnings + info)
- `#genai-critical` - Critical alerts only
- `#genai-cost-alerts` - Cost-related alerts
- `#genai-performance` - Performance issues

### 3. Start Alertmanager

```bash
docker-compose -f docker-compose.yml -f docker-compose.metrics.yml up -d
```

**Access:**
- Alertmanager UI: http://localhost:9093
- Prometheus alerts: http://localhost:9090/alerts

---

## Configuration

### Routing Rules

Alerts are routed based on:
1. **Severity** (critical/warning)
2. **Alert name pattern**
3. **Labels**

```yaml
route:
  routes:
    # Critical → Multiple channels
    - match:
        severity: critical
      receiver: 'critical-alerts'
    
    # Cost alerts → Dedicated channel
    - match_re:
        alertname: '.*Cost.*'
      receiver: 'cost-alerts'
```

### Receivers (Notification Channels)

#### Slack

```yaml
- name: 'slack'
  slack_configs:
    - channel: '#genai-alerts'
      title: '⚠️ Warning: {{ .GroupLabels.alertname }}'
      text: '{{ .Annotations.summary }}'
      send_resolved: true
```

#### Email

```yaml
- name: 'critical-alerts'
  email_configs:
    - to: 'oncall@example.com'
      from: 'alertmanager@genai-auto.com'
      smarthost: 'smtp.gmail.com:587'
      auth_username: 'alertmanager@genai-auto.com'
      auth_password: 'YOUR_EMAIL_PASSWORD'
```

**Gmail setup:**
1. Enable 2FA: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use app password (not Gmail password)

#### PagerDuty

```yaml
- name: 'critical-alerts'
  pagerduty_configs:
    - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
      description: '{{ .GroupLabels.alertname }}'
```

**PagerDuty setup:**
1. Services → New Service → API integration
2. Copy Integration Key
3. Paste as `service_key`

---

## Alert Routing Strategy

### By Severity

| Severity | Channels | Action |
|----------|----------|--------|
| **Critical** | Slack + Email + PagerDuty | Immediate response required |
| **Warning** | Slack only | Monitor, no immediate action |
| **Info** | Logs only | Informational |

### By Type

| Alert Type | Channel | Purpose |
|------------|---------|---------|
| Cost alerts | `#genai-cost-alerts` | Budget monitoring |
| Performance | `#genai-performance` | Latency/throughput issues |
| Errors | `#genai-alerts` | Application errors |
| Quality | `#genai-alerts` | RAG quality, routing accuracy |

---

## Inhibition Rules

Suppress redundant alerts:

```yaml
inhibit_rules:
  # API down → Suppress all other alerts
  - source_match:
      alertname: 'APIDown'
    target_match_re:
      alertname: '.*'
  
  # Critical cost → Suppress warning cost
  - source_match:
      alertname: 'CriticalLLMCost'
    target_match:
      alertname: 'HighLLMCost'
```

**Why?**
- Avoid alert fatigue
- Focus on root cause
- Reduce noise

---

## Notification Templates

Custom Slack message format:

**File:** `alertmanager/templates/slack.tmpl`

```go
{{ define "slack.default.text" }}
{{- range .Alerts }}
*Alert:* {{ .Labels.alertname }}
*Summary:* {{ .Annotations.summary }}
*Started:* {{ .StartsAt.Format "2006-01-02 15:04:05" }}
{{- end }}
{{ end }}
```

**Variables:**
- `.Labels` - Alert labels (alertname, severity, etc.)
- `.Annotations` - Alert annotations (summary, description)
- `.StartsAt` / `.EndsAt` - Alert timestamps
- `.Status` - firing or resolved

---

## Testing Alerts

### Manually Trigger Alert

```bash
# Send test alert
curl -H "Content-Type: application/json" -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning"
  },
  "annotations": {
    "summary": "This is a test alert",
    "description": "Testing Alertmanager configuration"
  }
}]' http://localhost:9093/api/v1/alerts
```

### Verify Alert Flow

1. Check Prometheus: http://localhost:9090/alerts
2. Check Alertmanager: http://localhost:9093/#/alerts
3. Check Slack/Email
4. Verify alert resolved

---

## Grouping & Throttling

### Grouping

Batch similar alerts:

```yaml
route:
  group_by: ['alertname', 'severity']
  group_wait: 10s       # Wait 10s to group
  group_interval: 10s   # Send grouped alerts every 10s
  repeat_interval: 4h   # Re-send if still firing after 4h
```

**Example:**
- 5 "High Latency" alerts within 10s → 1 grouped notification

### Throttling

Prevent alert spam:

```yaml
repeat_interval: 4h  # Don't repeat for 4 hours
```

---

## Alert Silencing

Temporarily silence alerts (maintenance windows):

**Via UI:**
1. Go to http://localhost:9093
2. Click "Silence" → "New Silence"
3. Add matchers (e.g., `alertname=HighLatency`)
4. Set duration
5. Add comment

**Via API:**
```bash
curl -X POST http://localhost:9093/api/v1/silences -d '{
  "matchers": [
    {"name": "alertname", "value": "HighLatency", "isRegex": false}
  ],
  "startsAt": "2024-01-01T00:00:00Z",
  "endsAt": "2024-01-01T02:00:00Z",
  "createdBy": "admin",
  "comment": "Planned maintenance"
}'
```

---

## Best Practices

### 1. Alert Fatigue Prevention

**Do:**
- ✅ Group similar alerts
- ✅ Use inhibition rules
- ✅ Set appropriate thresholds
- ✅ Send criticals to PagerDuty, warnings to Slack

**Don't:**
- ❌ Alert on everything
- ❌ Use same channel for all severities
- ❌ Set thresholds too low
- ❌ Repeat alerts every minute

### 2. Actionable Alerts

Every alert should answer:
- **What** is wrong?
- **Why** does it matter?
- **How** to fix it?

**Good:**
```
Summary: High LLM cost detected
Description: LLM spend exceeds $10/hour (current: $15.50)
Runbook: Check docs/runbooks/high-cost.md
```

**Bad:**
```
Summary: Alert triggered
Description: Metric above threshold
```

### 3. Runbooks

Link alerts to runbooks:

```yaml
annotations:
  summary: "High latency detected"
  description: "P95 latency exceeds 5s"
  runbook: "https://docs.example.com/runbooks/latency.md"
```

### 4. Test Regularly

- Test alert routing (weekly)
- Verify all receivers work
- Practice alert response
- Update on-call rotation

---

## Troubleshooting

### Alerts not firing

**Check Prometheus:**
```bash
# View pending alerts
curl http://localhost:9090/api/v1/alerts

# Check alert rules
curl http://localhost:9090/api/v1/rules
```

**Verify rule syntax:**
```bash
promtool check rules alerts.yml
```

### Notifications not sent

**Check Alertmanager status:**
```bash
curl http://localhost:9093/api/v1/status
```

**Test receiver:**
```bash
# Send test notification
amtool alert add alertname=test severity=warning \
  --alertmanager.url=http://localhost:9093
```

**Check Alertmanager logs:**
```bash
docker logs genai-alertmanager
```

### Slack webhook not working

**Common issues:**
- Invalid webhook URL
- Channel doesn't exist
- Bot not invited to channel
- Rate limiting

**Test webhook:**
```bash
curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test from Alertmanager"}'
```

---

## Advanced Configuration

### Routing Tree

```yaml
route:
  receiver: 'default'
  routes:
    - match: {severity: critical}
      receiver: 'pagerduty'
      continue: true  # Also match child routes
      
      routes:
        - match: {alertname: APIDown}
          receiver: 'pagerduty-high-priority'
        
        - match_re: {alertname: '.*Cost.*'}
          receiver: 'slack-and-email'
```

### Time-based Routing

```yaml
# Weekdays: PagerDuty
# Weekends: Slack only
route:
  routes:
    - match: {severity: critical}
      receiver: 'pagerduty'
      active_time_intervals:
        - weekdays
    
    - match: {severity: critical}
      receiver: 'slack'
      active_time_intervals:
        - weekends

time_intervals:
  - name: weekdays
    time_intervals:
      - weekdays: ['monday:friday']
  
  - name: weekends
    time_intervals:
      - weekdays: ['saturday', 'sunday']
```

---

## Monitoring Alertmanager

Monitor the monitor:

```yaml
# In prometheus.yml
- job_name: 'alertmanager'
  static_configs:
    - targets: ['alertmanager:9093']
```

**Metrics to track:**
- `alertmanager_notifications_total` - Total notifications sent
- `alertmanager_notifications_failed_total` - Failed notifications
- `alertmanager_alerts` - Current active alerts

---

## Resources

- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [PagerDuty Integration](https://www.pagerduty.com/docs/guides/prometheus-integration-guide/)
- [Alert Template Reference](https://prometheus.io/docs/alerting/latest/notifications/)

---

## Next Steps

1. ✅ Configure Slack webhook
2. ✅ Create notification channels
3. ✅ Start Alertmanager
4. ✅ Test alert flow
5. 🔜 Set up PagerDuty (optional)
6. 🔜 Create runbooks
7. 🔜 Define on-call rotation
