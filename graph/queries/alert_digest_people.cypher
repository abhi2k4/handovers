// Everyone with alert settings: the daily digest goes to those who keep it on.
MATCH (s:AlertSettings)
RETURN s.employee AS employee, s.phone AS phone, s.modes AS modes
