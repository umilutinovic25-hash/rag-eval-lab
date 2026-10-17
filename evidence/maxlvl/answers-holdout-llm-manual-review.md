# B3: ručni pregled LLM odgovora (holdout)

Stroga provera podniza (`answer_quality`) daje 13/23, jer model preformuliše činjenicu. Ručno su pregledana svih 10 odgovora koji nisu prošli strogu proveru, uz poređenje sa citiranim pasusom:

| ID | Očekivana činjenica | Odgovor modela (skraćeno) | Ručno |
| --- | --- | --- | --- |
| H02 | is required for email, vpn | MFA ... is required for using the VPN | tačno |
| H03 | never share passwords | you should never share your passwords, even with colleagues from IT | tačno |
| H05 | 31 march | carried over until March 31st | tačno |
| H08 | courses, conferences and certifications | courses, conferences, and certifications | tačno (zarez) |
| H10 | approved before booking | requires approval **from an appropriate authority** before you book | tačno, ali dodaje detalj kog nema u pasusu |
| H14 | reported to reception | report your lost badge to reception on the same day | tačno |
| H17 | 3 days per week | three days per week | tačno |
| H18 | two-week onboarding plan | lasts for two weeks | tačno |
| H20 | ordered through that same form | through the same form used for accessories like a mouse | tačno |
| H21 | report lost or stolen devices to security first | First, you should report the stolen device to security | tačno |

Ukupno: 23/23 činjenično tačno, 23/23 validne oznake `[chunk-id]`, a 1 odgovor (H10) ima nepodržanu dopunu. Na eval skupu stroga provera daje 9/9.
