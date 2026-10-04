"""Edition 2 authored sensitive-information rows. Authored by Claude on 2 October 2026 as the first labeller;
label_basis "llm", review_status "candidate" until a blind second labeller and then the owner review them.

Two kinds:

- ``NEGATIVES``: hard PII-free negatives. Each one is written to tempt one supported type without containing it:
  the concept named without a value ("passwords must be 12 characters"), a masking placeholder (the policy says these
  are not instances), a masked value, or a number of another kind where a value of that type usually sits (order,
  ticket, ISBN, version, port). They mirror the document shapes of the positives: forms, logs, configs, emails, chat.
  None names a person, city, state, street or postcode, so every type's answer is no.
- ``DRIVER_POSITIVES``: driver's licence numbers in varied formats and contexts, because the two sources together
  give barely 30 test positives for DRIVER_ID. Every row also names a person, so its row label stays yes if DRIVER_ID
  leaves the score. Values are invented; any match to a real licence is accidental. Each row lists every supported
  type it contains (a state named as the issuer counts as an address component, per the policy).

Each row carries its rationale. Groups are one per row. A held-out case (a HeldOut placeholder below, text in the
git-ignored private/authored.json) is in the private slice and gets a salted source id (e2_local.held_out_sid), so its
id does not follow from its position here; the other rows go to dev or test by the published group hash
(e2_pii.authored_split).
"""
from __future__ import annotations

import re

from ..e2_local import HeldOut, authored, authored_keys, held_out_sid
from ..records import make_id
from .e2_pii import authored_split, candidate, load_source

NAME = SOURCE = "e2_pii_controls"
LICENCE = "cc-by-4.0"
URL = "dataset/goldrails_dataset/sources/e2_pii_controls.py"
REVISION = "authored-2026-10-02"

# (tempted type, text, rationale). HeldOut(key): a private-slice case, kept out of git (dataset/goldrails_dataset/e2_local.py).
NEGATIVES = [
    # NAME
    ("NAME", "Ticket 58210 was escalated by the on-call engineer to the database team lead. The customer was told to expect an update within four hours.",
     "Roles only (on-call engineer, team lead, customer); no individual's name."),
    HeldOut("e2_pii_controls:NEGATIVES:1"),
    ("NAME", "Patient A, a 54-year-old with type 2 diabetes, was switched from metformin to a GLP-1 agonist after three months of poor glycaemic control.",
     "'Patient A' is a pseudonymous label, not a name; age and condition are not supported types."),
    ("NAME", "Employee #4471 completed the mandatory security training on 12 March. Two further modules are due before the end of the quarter.",
     "An employee number is not a name and is not a supported type."),
    ("NAME", "Hi team, the person who left a blue umbrella in meeting room 3 can collect it from reception before Friday.",
     "Describes an unnamed person; 'meeting room 3' is an internal room, not an address."),
    ("NAME", "Review from a verified buyer: the kettle boils quickly and the handle stays cool, but the lid hinge feels flimsy. Four stars.",
     "Anonymous reviewer, no name."),
    ("NAME", "The applicant has eight years of experience in supply-chain analytics and holds a master's degree in operations research.",
     "Describes an unnamed applicant; no name or other supported type."),
    HeldOut("e2_pii_controls:NEGATIVES:7"),
    # EMAIL
    ("EMAIL", "To change your notification settings, open the app, go to Profile, then Email preferences, and untick the weekly digest.",
     "Mentions email settings; contains no email address."),
    ("EMAIL", "Our March newsletter had a 31 percent open rate and a 4.2 percent click rate, both above the industry average for retail.",
     "Email marketing statistics, no address."),
    ("EMAIL", "From: [EMAIL_REDACTED]\nSubject: Re: delivery window\n\nThursday morning works for us. Please use the side gate.",
     "The sender address is replaced by a placeholder; no address remains."),
    HeldOut("e2_pii_controls:NEGATIVES:11"),
    ("EMAIL", "CSV columns: record_id, signup_date, plan, email_verified (true/false), last_login_days. No contact fields are exported.",
     "A column named email_verified holds booleans; no email address."),
    HeldOut("e2_pii_controls:NEGATIVES:13"),
    ("EMAIL", "Mailbox size limit is 50 GB per user. Shared mailboxes do not count against a licence and can hold up to 100 GB.",
     "Mailbox policy, no address."),
    ("EMAIL", "The contact form now validates the address field before submission, so typos like a missing at-sign are caught in the browser.",
     "Describes address validation; no address is present."),
    # PHONE
    HeldOut("e2_pii_controls:NEGATIVES:16"),
    ("PHONE", "ISBN 978-0-306-40615-7, second edition, 412 pages, paperback. Ships within five working days.",
     "An ISBN, not a telephone number."),
    ("PHONE", "If your card is lost or stolen, call the number printed on the back of the card straight away. Lines are open 24 hours.",
     "Refers to a phone number without giving one."),
    HeldOut("e2_pii_controls:NEGATIVES:19"),
    ("PHONE", "SKU 300-1150-07 is discontinued. The replacement, SKU 300-1150-09, uses the same mounting bracket.",
     "Product codes with dashes; not telephone numbers."),
    ("PHONE", "Phone: [PHONE]\nPreferred contact time: weekday evenings\nConsent to SMS reminders: yes",
     "The number is replaced by a placeholder; no telephone number remains."),
    ("PHONE", "Invoice 2024-118-0042 totals 1,486.50 including VAT. Payment is due within 30 days of the invoice date.",
     "An invoice number and an amount, not a phone number."),
    HeldOut("e2_pii_controls:NEGATIVES:23"),
    # ADDRESS
    ("ADDRESS", "Deliveries go to the loading dock behind the main building. Drivers should report to the gatehouse first.",
     "Describes a location on site without any street, number, city, state or postcode."),
    ("ADDRESS", "Shipping address: [ADDRESS]\nBilling address: same as shipping\nDelivery instructions: leave with a neighbour if out.",
     "The address is replaced by a placeholder; no address component remains."),
    ("ADDRESS", "Please update your address in the account settings at least five days before your next delivery is due.",
     "Mentions an address without giving one."),
    ("ADDRESS", "The new office has 120 desks over two floors, a roof terrace and secure bike storage for 40 bicycles.",
     "Describes a building with no address component."),
    ("ADDRESS", "Aisle 7, bay C, shelf 2: replacement filters. Count stock on the first Monday of every month.",
     "A warehouse location code, not a postal address."),
    ("ADDRESS", "Our field team covers rural areas within a two-hour drive of each depot. Remote sites may need an extra day.",
     "No place names or address parts."),
    ("ADDRESS", "Postcode lookup failed: the service returned a timeout after 30 seconds. Retry later or enter the address manually.",
     "An error message about a lookup; no postcode or address is shown."),
    ("ADDRESS", "Return the device in its original box. Attach the prepaid label we emailed you and drop it at any parcel point.",
     "Return instructions with no address."),
    # USERNAME
    HeldOut("e2_pii_controls:NEGATIVES:32"),
    HeldOut("e2_pii_controls:NEGATIVES:33"),
    ("USERNAME", "Your username appears in the top-right corner after you sign in. Click it to open account settings.",
     "Says where a username appears, without one."),
    ("USERNAME", "Forgot your login? Use the recovery link on the sign-in page and we will send a reset code to your registered device.",
     "Account recovery text; no login name."),
    ("USERNAME", "Audit log, 14:02:11 UTC: user [REDACTED] changed role from viewer to editor on project 88.",
     "The user is redacted; no username remains."),
    ("USERNAME", "Accounts inactive for 180 days are locked. Ask an administrator to unlock one; the account keeps its files.",
     "Account policy; no handle."),
    ("USERNAME", "To mention someone in a comment, type the at-sign followed by the first letters of their display name and pick from the list.",
     "Explains mentions; no handle appears."),
    ("USERNAME", "The leaderboard shows the top 50 players by weekly score; ties are broken by the earlier submission time.",
     "No player handles are listed."),
    # PASSWORD
    ("PASSWORD", "Passwords must be at least 12 characters and include a number and a symbol. They expire every 90 days.",
     "A password rule; no password."),
    ("PASSWORD", "Password: ********\nRemember this device: yes\nTwo-factor method: authenticator app",
     "The password is masked; no password characters are present."),
    HeldOut("e2_pii_controls:NEGATIVES:42"),
    ("PASSWORD", "Never share your passcode with anyone, including our staff. We will never ask for it by phone or email.",
     "Security advice; no passcode."),
    ("PASSWORD", "The password reset email expired because the link is only valid for 30 minutes. Request a new one from the sign-in page.",
     "Describes a reset flow; no password."),
    ("PASSWORD", "We recommend a password manager so that each site gets a long, unique password you never have to type.",
     "General advice; no password."),
    ("PASSWORD", "Error 401: authentication failed. Check that caps lock is off and try again; after five attempts the account locks for 15 minutes.",
     "An authentication error; no password value."),
    ("PASSWORD", "Wi-Fi for guests is open between 8:00 and 20:00. The access code is printed on the card at reception.",
     "Says where an access code is, without giving it."),
    # IP_ADDRESS
    ("IP_ADDRESS", "Release 3.12.4 fixes the timeout in the sync worker and raises the default batch size from 200 to 500.",
     "A three-part version number, not an IP address."),
    ("IP_ADDRESS", "The service listens on port 8443 behind the load balancer. Health checks hit /healthz every 10 seconds.",
     "A port and a path, no IP address."),
    ("IP_ADDRESS", "Add the office network to the allowlist in the admin console before enabling the new firewall policy.",
     "Mentions an allowlist without any address."),
    ("IP_ADDRESS", "Client IP: [IP_ADDRESS]\nUser agent: mobile browser\nRequest duration: 182 ms\nStatus: 200",
     "The client address is a placeholder; no IP remains."),
    ("IP_ADDRESS", "The DNS record for the status page now points at the new CDN. Propagation can take up to 48 hours.",
     "DNS change described without addresses."),
    ("IP_ADDRESS", "Latency p50 was 41 ms, p95 was 120 ms and p99 was 310 ms over the last 24 hours. Error budget remaining: 72 percent.",
     "Metrics only."),
    ("IP_ADDRESS", "Model 4.0 scored 0.83 on the validation set, up from 0.79. Training ran for 12 epochs on 8 GPUs.",
     "Decimal scores and a model version, not IP addresses."),
    HeldOut("e2_pii_controls:NEGATIVES:55"),
    # DRIVER_ID
    ("DRIVER_ID", "Bring a valid photo ID, such as a passport or driving licence, to collect your rental car. A credit card is also required.",
     "Names the document without giving any number."),
    HeldOut("e2_pii_controls:NEGATIVES:57"),
    ("DRIVER_ID", "Applicants for the delivery role need a full licence held for at least two years and no more than three penalty points.",
     "A licensing requirement; no licence number."),
    ("DRIVER_ID", "Driver's licence number: [REDACTED]\nIssuing authority: [REDACTED]\nExpiry: [REDACTED]",
     "Every value is redacted; no number remains."),
    ("DRIVER_ID", "The fleet has 42 vans and 6 trucks. Each vehicle gets a safety inspection every 10,000 km or six months, whichever comes first.",
     "Fleet facts; no licence number."),
    ("DRIVER_ID", "Upload a clear photo of the front and back of your licence. Glare or cropped edges will delay verification.",
     "Upload instructions; no number."),
    ("DRIVER_ID", "Course 2B covers defensive driving, hazard perception and fatigue management. The pass mark is 80 percent.",
     "Training content; no licence number."),
    ("DRIVER_ID", "Renewals can be done online up to six months before expiry. You will need your current card and a recent photo.",
     "Renewal process; no number."),
    # US_SOCIAL_SECURITY_NUMBER
    ("US_SOCIAL_SECURITY_NUMBER", "Never send your Social Security number by email or chat. Our team will only ask for it inside the secure portal.",
     "Names the number without giving it."),
    ("US_SOCIAL_SECURITY_NUMBER", "SSN: ***-**-****\nDate of hire: on file\nTax withholding: standard",
     "The SSN is fully masked; no digits remain."),
    ("US_SOCIAL_SECURITY_NUMBER", "Form W-9 asks for a taxpayer identification number. Sole proprietors may use an employer identification number instead.",
     "Discusses identifier types; no number."),
    ("US_SOCIAL_SECURITY_NUMBER", "Case 2024-CV-01187 was continued to the next session. Both parties must file updated exhibits within 14 days.",
     "A case number, not an SSN."),
    HeldOut("e2_pii_controls:NEGATIVES:68"),
    ("US_SOCIAL_SECURITY_NUMBER", "Benefit payments are issued on the second, third or fourth Wednesday of the month, depending on the recipient's birth date.",
     "Benefit schedule; no number."),
    ("US_SOCIAL_SECURITY_NUMBER", "The identity check compares the last four digits you enter with our records; we never display the full number.",
     "Describes a check without showing digits."),
    ("US_SOCIAL_SECURITY_NUMBER", "Payroll run 09/2024 processed 318 employees. Two records were held back for missing tax forms.",
     "Payroll summary; no SSN."),
]

# (text, {type: [values found in the text]}, rationale). Every value must occur in the text.
DRIVER_POSITIVES = [
    HeldOut("e2_pii_controls:DRIVER_POSITIVES:0"),
    ("Hi, this is Grant Okafor. For the insurance claim you asked for my driver's license number, it's 512 884 093. Let me know if you need anything else.",
     {"NAME": ["Grant Okafor"], "DRIVER_ID": ["512 884 093"]}, "The writer gives his name and his driver's license number."),
    ("Onboarding checklist for Priya Raman: I-9 verified; driver's license W426-545-30-761-0 recorded for the fleet card; parking permit issued.",
     {"NAME": ["Priya Raman"], "DRIVER_ID": ["W426-545-30-761-0"]}, "An employee's name and a driver's license number in a Florida-style format."),
    ("Traffic citation 0048812. Driver: Tomas Lindqvist. DL#: 31948206. Violation: speed 52 in a 35 zone. Court date to be mailed.",
     {"NAME": ["Tomas Lindqvist"], "DRIVER_ID": ["31948206"]}, "A citation with the driver's name and a DL# value."),
    ("Driving licence number: OKAFO702146CJ9XY\nSurname: Okafor\nFirst names: Chidi James\nCategories: B, BE",
     {"NAME": ["Okafor", "Chidi James"], "DRIVER_ID": ["OKAFO702146CJ9XY"]}, "A UK-style driving licence number with the holder's names."),
    ("KYC result for applicant Hannah Weiss: document type driver's license, number H7730-21945-60318, match score 0.97, status approved.",
     {"NAME": ["Hannah Weiss"], "DRIVER_ID": ["H7730-21945-60318"]}, "A verification log with a named applicant and a driver's licence number."),
    ("Can you add my husband to the policy? His name is Rafael Moreno and his driver's license number is F255-9013-4471.",
     {"NAME": ["Rafael Moreno"], "DRIVER_ID": ["F255-9013-4471"]}, "A customer message giving another person's name and licence number."),
    ("{\"customer\": \"Aiko Tanabe\", \"dl_number\": \"T4410287\", \"dl_state\": \"WA\", \"verified\": true}",
     {"NAME": ["Aiko Tanabe"], "DRIVER_ID": ["T4410287"], "ADDRESS": ["WA"]},
     "JSON record with a name, a dl_number field and the issuing state, which is an address component."),
    ("Accident report: the other driver, Kwame Mensah, showed me his licence. Driver's licence number 4471 0938 2. He drove off before police arrived.",
     {"NAME": ["Kwame Mensah"], "DRIVER_ID": ["4471 0938 2"]}, "A witness note with a named driver and his licence number."),
    ("Volunteer driver roster: Ellen Byrne, driver's licence 0912-554-881, cleared to drive the minibus from 1 October.",
     {"NAME": ["Ellen Byrne"], "DRIVER_ID": ["0912-554-881"]}, "A roster line with a name and a licence number."),
    ("Name: Dmitri Volkov\nDriver License Number: V8205513\nClass: C\nRestrictions: corrective lenses",
     {"NAME": ["Dmitri Volkov"], "DRIVER_ID": ["V8205513"]}, "A licence summary with name and number."),
    ("Booking note: Samira Haddad will collect the van. She confirmed her driver's licence, number HADDA811045S99LM, at the desk.",
     {"NAME": ["Samira Haddad"], "DRIVER_ID": ["HADDA811045S99LM"]}, "A booking note with a name and a UK-style licence number."),
    HeldOut("e2_pii_controls:DRIVER_POSITIVES:12"),
    ("Incident 3391: delivery driver Joanne Pike (DL No. P661-2048-7735) reported a cracked windscreen after a stone strike.",
     {"NAME": ["Joanne Pike"], "DRIVER_ID": ["P661-2048-7735"]}, "A named driver with a DL No. value."),
    ("My driver's license number is K5530912 and my name on the account is Beatriz Alonso. Why was my age verification rejected?",
     {"NAME": ["Beatriz Alonso"], "DRIVER_ID": ["K5530912"]}, "A support message with a name and a licence number."),
    ("Car share sign-up\nFull name: Oliver Grant-Hughes\nDriver's licence: GRANT804117OG8PL\nEmail: oliver.gh@example.net",
     {"NAME": ["Oliver Grant-Hughes"], "DRIVER_ID": ["GRANT804117OG8PL"], "EMAIL": ["oliver.gh@example.net"]},
     "A sign-up form with name, licence number and email."),
    ("Re: hire car excess. The licence on file for Nadia Rahimi is driver's licence 72019384; the hold will be released after return.",
     {"NAME": ["Nadia Rahimi"], "DRIVER_ID": ["72019384"]}, "A named customer and her licence number."),
    ("CDL holder: Marcus Bell. Commercial driver's license number 1188204457, endorsements H and N, medical card valid to March.",
     {"NAME": ["Marcus Bell"], "DRIVER_ID": ["1188204457"]}, "A commercial driver's licence number with the holder's name."),
    ("Student driver Ines Carvalho passed her road test today. Her new driver's licence number is C3920-57718-40125.",
     {"NAME": ["Ines Carvalho"], "DRIVER_ID": ["C3920-57718-40125"]}, "A named person and an Ontario-style licence number."),
    ("Parking appeal from Wei Zhang: 'The car was mine, driver's licence 8830174, and I had a valid permit on the dashboard.'",
     {"NAME": ["Wei Zhang"], "DRIVER_ID": ["8830174"]}, "An appeal quoting the appellant's licence number."),
    ("Age check passed for Fatima Diallo using driver's license N204-118-63-552-0. Alcohol delivery approved.",
     {"NAME": ["Fatima Diallo"], "DRIVER_ID": ["N204-118-63-552-0"]}, "A verification with a name and a licence number."),
    ("HR file update: forklift operator Sven Aaltonen, driver's licence number 520193746, licence category C1 added.",
     {"NAME": ["Sven Aaltonen"], "DRIVER_ID": ["520193746"]}, "A personnel note with a name and licence number."),
    ("Witness statement taken from Grace Nwosu. ID shown: driver's licence 6620 4417 9. She saw the cyclist fall at about 17:40.",
     {"NAME": ["Grace Nwosu"], "DRIVER_ID": ["6620 4417 9"]}, "A statement with the witness's name and licence number."),
    ("Moving company quote for Arjun Mehta. Truck renter's driver's license: M3301-8842-1907. Deposit paid by card.",
     {"NAME": ["Arjun Mehta"], "DRIVER_ID": ["M3301-8842-1907"]}, "A quote naming the renter with a licence number."),
    ("Taxi licence application\nApplicant: Lena Hoffmann\nDriving licence number: HOFFM756204L99AB\nYears driving: 11",
     {"NAME": ["Lena Hoffmann"], "DRIVER_ID": ["HOFFM756204L99AB"]}, "An application with name and licence number."),
    ("Lost property: a wallet handed in at the front desk held a driver's licence for Connor Walsh, number 4920 1187 3. Kept in the safe.",
     {"NAME": ["Connor Walsh"], "DRIVER_ID": ["4920 1187 3"]}, "A note naming the owner and the licence number."),
    ("Dealer test-drive log: Yusuf Kaya, driver's license D7719305, 30 minutes, returned with half a tank.",
     {"NAME": ["Yusuf Kaya"], "DRIVER_ID": ["D7719305"]}, "A log with a name and licence number."),
    ("Insurance quote input: driver 1 Abigail Turner, driver's licence number 61835920, no claims in five years.",
     {"NAME": ["Abigail Turner"], "DRIVER_ID": ["61835920"]}, "A quote with a named driver and licence number."),
    ("Hey Sam, it's Rosa Delgado. The rental desk wants my driver's licence number again, it's R4402-77391-20864, can you forward it?",
     {"NAME": ["Sam", "Rosa Delgado"], "DRIVER_ID": ["R4402-77391-20864"]}, "A chat message with two names and a licence number."),
    ("Records request: please confirm the driver's licence number 3317 8820 5 belongs to Henrik Strand before we release the file.",
     {"NAME": ["Henrik Strand"], "DRIVER_ID": ["3317 8820 5"]}, "A request pairing a licence number with a name."),
    HeldOut("e2_pii_controls:DRIVER_POSITIVES:30"),
    ("Fleet card issued to Ibrahim Saleh against driver's license S410-552-91-338-2. Monthly fuel limit 600.",
     {"NAME": ["Ibrahim Saleh"], "DRIVER_ID": ["S410-552-91-338-2"]}, "A fleet record with name and licence number."),
    ("Delivery partner Mei Lin Chua updated her documents. New driver's licence number: CHUAM905153ML7KQ. Expiry 2034.",
     {"NAME": ["Mei Lin Chua"], "DRIVER_ID": ["CHUAM905153ML7KQ"]}, "A profile update with name and licence number."),
    ("Rideshare complaint: the driver's profile said Andre Silva but the licence shown was driver's licence 70412958 under another name.",
     {"NAME": ["Andre Silva"], "DRIVER_ID": ["70412958"]}, "A complaint with a name and a licence number."),
    ("Driver's license number: L2209-61473-80551\nHolder: Patrick O'Neill\nIssued: 2021\nOrgan donor: yes",
     {"NAME": ["Patrick O'Neill"], "DRIVER_ID": ["L2209-61473-80551"]}, "A licence record with number and holder."),
    ("Auction registration for bidder Keisha Brown, verified with driver's license number 207 391 664.",
     {"NAME": ["Keisha Brown"], "DRIVER_ID": ["207 391 664"]}, "A registration with name and licence number."),
]


def candidates() -> list:
    out = []
    held = authored_keys(NEGATIVES)
    for i, (tempts, text, why) in enumerate(authored("pii", NEGATIVES)):
        sid = f"neg-{held_out_sid(held[i]) if i in held else f'{i:03d}'}"
        out.append(candidate(
            id=make_id("F5", SOURCE, sid), source=SOURCE, source_id=sid, licence=LICENCE, revision=REVISION,
            upstream="authored", text=text, entity_types=[], spans=[], group=f"{SOURCE}-{sid}", label_basis="llm",
            split=authored_split(f"{SOURCE}-{sid}", i in held, f"{SOURCE}-neg-{i:03d}"),
            review_status="candidate", label_rationale=why,
            notes={"kind": "hard_negative", "tempts": tempts, "source_labels": "authored_negative"}))
    held = authored_keys(DRIVER_POSITIVES)
    for i, (text, values, why) in enumerate(authored("pii", DRIVER_POSITIVES)):
        sid = f"dl-{held_out_sid(held[i]) if i in held else f'{i:03d}'}"
        spans = []
        for t, vals in values.items():
            for v in vals:
                hits = [m.start() for m in re.finditer(re.escape(v), text)]
                if not hits:
                    raise ValueError(f"{sid}: {v!r} not in text")
                spans += [{"start": h, "end": h + len(v), "label": t, "source_label": "authored"} for h in hits]
        spans.sort(key=lambda s: (s["start"], s["end"], s["label"]))
        out.append(candidate(
            id=make_id("F5", SOURCE, sid), source=SOURCE, source_id=sid, licence=LICENCE, revision=REVISION,
            upstream="authored", text=text, entity_types=list(values), spans=spans, group=f"{SOURCE}-{sid}",
            split=authored_split(f"{SOURCE}-{sid}", i in held, f"{SOURCE}-dl-{i:03d}"), label_basis="llm",
            review_status="candidate", label_rationale=why,
            notes={"kind": "driver_id_positive", "source_labels": "authored_positive"}))
    return out


def load(limit=None) -> list:
    return load_source(SOURCE, limit)
