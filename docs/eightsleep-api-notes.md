# Eight Sleep API notes

- Inspect raw JSON. Change one setting in iOS, then diff the responses to see which fields actually move.
- Search community client source for those field names. Verify candidate writes with a small reversible change, read back the result, then restore and verify again.
- Bedtime example: iOS changed both `currentLevel` and `currentSchedule.startSettings.bedtime`. The [pyEight bedtime code](https://github.com/lukas-clarke/pyEight/blob/main/pyEight/user.py) pointed to `PUT /v1/users/{id}/bedtime`, which reproduced both changes with the existing schedule preserved. The [Home Assistant API notes](https://github.com/lukas-clarke/eight_sleep/issues/138) helped identify the schedule fields.
