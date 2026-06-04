# `constants/` — values that never change

Genuine constants only: enums, fixed lookup tables, protocol strings.
`UPPER_CASE` names are correct *here*. If a value differs between dev and prod,
it is configuration, not a constant — put it in `config/settings.py` instead.
No secrets, ever.
