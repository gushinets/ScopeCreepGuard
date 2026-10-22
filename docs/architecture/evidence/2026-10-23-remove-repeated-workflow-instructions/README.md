# Remove repeated workflow instructions

Removed the idle assessment teaching block (including its heading), the repeated empty-request instruction below Check scope, and the unselected History detail instruction block. Removed their unused Russian/English translations. Field labels/placeholders, validations, terms-changed feedback, all actual results/actions, and the single contextual onboarding guide remain.

Docker build/typecheck and frontend lint/boundaries passed. Frontend suite: 376 tests across 51 files passed; the existing Python/JOSE interoperability test remains excluded from the Node-only image.

Browser verification used synthetic accounts against the local Docker app at port 3000 in RU/EN, desktop 1440x1000 and mobile 390x844. Created a project, verified one contextual coachmark and no idle assessment instructions, skipped onboarding, checked the main action becomes available after input, and reloaded. No horizontal overflow. No AI calls. Screenshots were visually inspected; the updated build is installed locally.

- [Russian desktop](no-repeat-ru-desktop.png)
- [Russian mobile](no-repeat-ru-mobile.png)
- [English desktop](no-repeat-en-desktop.png)
- [English mobile](no-repeat-en-mobile.png)
