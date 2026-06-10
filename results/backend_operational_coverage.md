# GrapeMaster Backend Operational Coverage

- Raw deduplicated accounts: 95
- Retained operational accounts: 47
- Excluded accounts: 48
- Screening rule: Retain accounts with at least one field and at least one crop season; summarize downstream records linked to retained accounts, retained fields, retained crop seasons, or retained tasks.

| Workflow domain | Backend object | Records | Linked units |
| --- | --- | ---: | --- |
| Account and field setup | Retained operational accounts | 47 | accounts with >=1 field and >=1 crop season |
| Account and field setup | Vineyard fields | 139 | 47 retained accounts |
| Account and field setup | Crop seasons | 128 | 139 retained fields |
| Environmental and analytical state | Weather payloads | 126 | 126 crop seasons |
| Environmental and analytical state | Phenology payloads | 126 | 126 crop seasons |
| Environmental and analytical state | Disease-risk outputs | 252 | 126 crop seasons |
| Risk delivery and field operations | Notifications | 3590 | 125 crop seasons |
| Risk delivery and field operations | Plant-protection and irrigation tasks | 151 | 55 crop seasons |
| Risk delivery and field operations | Fungicide and pesticide records | 234 | 141 plant-protection tasks |
| Field evidence and consultation | Field notes and disease reports | 94 | crop seasons, fields, or retained accounts |
| Field evidence and consultation | Image-analysis records | 2808 | retained accounts or uploaded images |
| Field evidence and consultation | Advisory and message records | 1360 | 27 retained accounts |
| Community communication | Forum records | 27 | 7 retained accounts |
