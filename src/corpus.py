from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    section: str
    version: str
    status: str  # "current" or "superseded"
    text: str


HANDBOOK: list[Document] = [
    Document(
        doc_id="hb-01",
        title="Equipment replacement",
        section="IT and equipment",
        version="2026",
        status="current",
        text=(
            "Laptop replacement: broken, lost or stolen laptops can be replaced. After manager "
            "approval, a replacement laptop is set up by IT staff with your files, accounts, email "
            "and access rights, and handover can take up to 5 business days. Report lost or stolen "
            "devices to security first. Request a replacement laptop in IT portal under Hardware. "
            "Accessories such as mouse or headset are ordered through that same form."
        ),
    ),
    Document(
        doc_id="hb-02",
        title="Remote work policy",
        section="Working arrangements",
        version="2024",
        status="superseded",
        text=(
            "Remote work: employees can work remotely up to 2 days per week. Remote days per week are "
            "agreed with your team lead. Remote work days can be moved within same week."
        ),
    ),
    Document(
        doc_id="hb-03",
        title="Remote work policy",
        section="Working arrangements",
        version="2026",
        status="current",
        text=(
            "Remote work: employees can work remotely up to 3 days per week. Remote days per week are "
            "agreed with your team lead and recorded in your shared team calendar. Remote work days "
            "can be moved within same week. Core hours from 10:00 to 15:00 apply on remote days, and "
            "you must be reachable by chat and phone during core hours."
        ),
    ),
    Document(
        doc_id="hb-04",
        title="Travel expenses",
        section="Finance",
        version="2026",
        status="current",
        text=(
            "Business travel must be approved before booking. Travel receipts must be submitted "
            "within 30 days of your return, through finance app. Keep original receipts "
            "for hotels and flights. Daily allowances follow national rules for each destination."
        ),
    ),
    Document(
        doc_id="hb-05",
        title="Passwords and access",
        section="Security",
        version="2026",
        status="current",
        text=(
            "Passwords must be changed every 90 days and must contain at least 12 characters. "
            "Multi-factor authentication (MFA) is required for email, VPN and all internal tools. "
            "Never share passwords, also not with colleagues from IT."
        ),
    ),
    Document(
        doc_id="hb-06",
        title="Onboarding",
        section="People",
        version="2026",
        status="current",
        text=(
            "New colleagues follow a two-week onboarding plan. A buddy is assigned in your first week "
            "and helps you get started with tools, people and team habits. Your manager schedules a "
            "check-in at end of month one and again after three months."
        ),
    ),
    Document(
        doc_id="hb-07",
        title="Annual leave",
        section="People",
        version="2026",
        status="current",
        text=(
            "Annual leave policy: employees get 22 days of annual leave per calendar year. "
            "Leave requests must be made two weeks in advance in HR portal. "
            "Under this policy, unused leave can be carried over until 31 March. "
            "Sick leave follows a separate policy."
        ),
    ),
    Document(
        doc_id="hb-08",
        title="Training budget",
        section="Learning",
        version="2026",
        status="current",
        text=(
            "Each employee has a training budget of 800 EUR per year for courses, conferences "
            "and certifications. Agree training with your manager before booking. "
            "Unused budget does not carry over to next year."
        ),
    ),
    Document(
        doc_id="hb-09",
        title="Office access and parking",
        section="Facilities",
        version="2026",
        status="current",
        text=(
            "Office access requires your personal badge at every entrance. Lost badges must be "
            "reported to reception on same day. Parking is limited: spaces are shared and "
            "reserved through facilities app, first come, first served."
        ),
    ),
    Document(
        doc_id="hb-10",
        title="IT support",
        section="IT and equipment",
        version="2026",
        status="current",
        text=(
            "IT support hours are 08:00 to 18:00, Monday to Friday. Contact support through "
            "IT portal or by phone. For a laptop that does not start, bring it to IT desk "
            "on floor two. Outside support hours, urgent security incidents go to on-call line."
        ),
    ),
]


def load_corpus() -> list[Document]:
    return list(HANDBOOK)
