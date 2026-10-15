// One person's alert settings: WhatsApp number, email on or off, mode per alert kind (JSON), quiet hours.
MATCH (s:AlertSettings {employee: $emp})
RETURN s.phone AS phone, s.email AS email, s.modes AS modes, s.quiet_from AS quiet_from, s.quiet_to AS quiet_to
