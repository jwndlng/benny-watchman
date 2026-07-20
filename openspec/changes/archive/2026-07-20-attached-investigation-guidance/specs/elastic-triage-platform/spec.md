## MODIFIED Requirements

### Requirement: Elastic alerts map to the SIEM Alert schema
The platform SHALL map an Elastic alert document to the SIEM `Alert`: `id`←`_id`, `type`←`kibana.alert.rule.name`, `title`←`kibana.alert.rule.name`, `description`←`kibana.alert.reason`, `severity`←`kibana.alert.severity`, `source`←`"elastic"`, `timestamp`←`@timestamp`, `raw`←the full document, and `guidance`←the rule investigation note (see below). The `type` mapping is plain metadata and dedup input — it no longer selects a runbook.

#### Scenario: An alert document becomes a valid Alert payload
- **WHEN** an Elastic alert document is fetched and mapped
- **THEN** the resulting payload validates as an `Alert`, its `type` reflects the rule name as metadata, and `guidance` is populated when the rule has an investigation note

## ADDED Requirements

### Requirement: Investigation guidance is sourced from the detection rule note
The platform SHALL populate `Alert.guidance` from the detection rule's investigation note with `source` = `"elastic-rule-note"`. It SHALL read the note from the alert document when present and otherwise fetch the rule once, caching the note per rule uuid so cost is per unique rule, not per alert. When the rule has no note, `guidance` SHALL be `None`.

#### Scenario: Rule note becomes guidance
- **WHEN** an alert's detection rule has an investigation note
- **THEN** the mapped `Alert.guidance.text` is the note and `guidance.source` is `"elastic-rule-note"`

#### Scenario: Note resolution is cached per rule
- **WHEN** multiple open alerts share the same detection rule
- **THEN** the rule note is resolved once and reused for all of them

#### Scenario: No note yields no guidance
- **WHEN** an alert's detection rule has no investigation note
- **THEN** the mapped `Alert.guidance` is `None`
