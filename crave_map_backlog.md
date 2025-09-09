CraveMap Backlog

Index
BL-01 Promo section quick-jump
BL-02 Always-visible promo input
BL-03 Clear post-apply promo summary
BL-04 Free-tier rate limit message clarity
BL-05 Immediate counter updates
BL-06 Blank search validation
BL-07 Location apply UX
BL-08 Premium upgrade copy safety
BL-09 Premium support gating
BL-10 Search result feedback toast
BL-11 Mobile quick-nav and spacing
BL-12 Analytics events for key actions
BL-13 Error boundary and friendly fallback
BL-14 Promo input discoverability on limit
BL-15 Consistent sidebar status
BL-16 Prevent accidental payment in test
BL-17 Results section jump link
BL-18 Copiable error and support codes
BL-19 Toast on promo apply outcome
BL-20 Keyboard accessibility polish

BL-01 Title
Promo section quick-jump
User Story
As a free user, I want a visible Have a promo code? button near the search form that scrolls to the promo section, so that I can apply a promo without hunting through the page.
Acceptance Criteria
1. A secondary button labeled Have a promo code? is placed below Find Food.
2. Clicking it scrolls to and expands the promo code input.
3. Focus moves into the promo input after scroll.
Dev Notes
Use smooth anchor scroll to promo container. Ensure works on desktop and mobile.

BL-02 Title
Always-visible promo input
User Story
As any user, I want the promo input to be visible without expanders, so that I immediately understand where to enter codes.
Acceptance Criteria
1. Promo code input is visible by default.
2. Apply Code button is always present and enabled only when input is non-empty.
3. No collapsible arrow is shown for the promo input.
Dev Notes
Replace expander with a standard input row in the promo section.

BL-03 Title
Clear post-apply promo summary
User Story
As any user, I want a clear summary of active promo effects, so that I understand my current plan, limits, and what changed.
Acceptance Criteria
1. After applying a code, show a summary card with code, effect, and current limits.
2. Provide a Downgrade to free action when premium is via promo.
3. Invalid or expired codes show inline error Invalid promo code. Please check and try again.
Dev Notes
Centralize promo effects in session state and surface in one component.

BL-04 Title
Free-tier rate limit message clarity
User Story
As a free user, I want a friendly, specific limit message, so that I know when I can search again and what my options are.
Acceptance Criteria
1. On 4th search in a day, show red banner You have used all 3 free searches today on this device or network. Resets at 12:00am local time.
2. Banner includes Have a promo code? and Create Account buttons.
3. Banner disappears once the day rolls over or a valid premium code is applied.
Dev Notes
Enforce limits server-side as well as client-side.

BL-05 Title
Immediate counter updates
User Story
As a user, I want the search counter in the sidebar to update immediately after each search, so that the remaining count is always accurate.
Acceptance Criteria
1. After a successful search, remaining count updates without page refresh.
2. After resetcounter, counter resets to full allowance instantly.
3. After resetfree, tier switches to Free and counter reflects free allowance.
Dev Notes
Single source of truth in session state. Trigger rerender on mutations.

BL-06 Title
Blank search validation
User Story
As a user, I want helpful inline messages when I try to search with empty fields, so that I know what to fix.
Acceptance Criteria
1. If craving is empty, show hint under field Please enter what you are craving.
2. If location is empty, show hint under field Please enter a city or area.
3. Clicking Find Food with blanks shows hints and does not execute the search.
4. Hints clear as soon as the user starts typing in the field.
Dev Notes
Add client-side checks before calling the backend.

BL-07 Title
Location apply UX
User Story
As a user, I want typed location changes to apply automatically, so that I do not have to press Enter to confirm.
Acceptance Criteria
1. Red outline and Press Enter to apply no longer appear.
2. Typing in the location input updates the internal value immediately.
Dev Notes
Remove commit-on-Enter behavior. Use onChange to commit.

BL-08 Title
Premium upgrade copy safety
User Story
As a promo-upgraded user, I want copy that makes it obvious I am not being billed, so that I am not confused by Subscription active messages.
Acceptance Criteria
1. If premium is via promo, display Premium via promo code. No charges applied.
2. If premium is via paid subscription, display Subscription active with price.
Dev Notes
Add a flag to distinguish promo vs paid premium and branch the copy.

BL-09 Title
Premium support gating
User Story
As a premium user, I want to see the support form, so that I can contact support.
Acceptance Criteria
1. Premium Support section is visible only when premium is active.
2. Submit button is disabled when SAFE_MODE is true.
3. Show disclaimer Submitting sends a real email. Do not submit during testing.
Dev Notes
Honor SAFE_MODE environment flag and disable submit accordingly.

BL-10 Title
Search result feedback toast
User Story
As a user, I want immediate feedback after clicking Find Food, so that I know a search is running and when it finishes.
Acceptance Criteria
1. Show toast Searching… when a search starts.
2. Show Found N places or No matches found after completion.
3. Toasts do not overlap promo or support sections.
Dev Notes
Use a small status container or toast utility.

BL-11 Title
Mobile quick-nav and spacing
User Story
As a mobile user, I want fast navigation and readable spacing, so that I can reach promo, results, and support easily on a small screen.
Acceptance Criteria
1. Add bottom sticky mini-nav with buttons Search, Promo, Results, Support for screens under 480px width.
2. Inputs and buttons have at least 44px touch targets.
Dev Notes
Media queries; avoid hiding core actions behind long scrolls.

BL-12 Title
Analytics events for key actions
User Story
As the product owner, I want analytics for promo apply, limit reached, and search executed, so that I can monitor usage and troubleshoot.
Acceptance Criteria
1. Emit search_performed with flags has_craving, has_location, results_count.
2. Emit rate_limit_hit with tier and device_id or session fingerprint.
3. Emit promo_applied with code and outcome success or failure.
4. No PII is sent in events.
Dev Notes
Gate analytics behind a config flag. Batch if needed.

BL-13 Title
Error boundary and friendly fallback
User Story
As any user, I want a friendly fallback if the search service errors, so that I understand what to try next.
Acceptance Criteria
1. On backend failure or timeout, show banner We are having trouble fetching places. Please try again in a moment.
2. Provide a Retry button that re-runs the last query.
Dev Notes
Wrap search call in try or except and store lastQuery in session.

BL-14 Title
Promo input discoverability on limit
User Story
As a rate-limited user, I want the limit message to include a one-click reveal for the promo input, so that I can apply a code immediately.
Acceptance Criteria
1. Limit banner includes Apply promo code button that scrolls to promo input and focuses it.
2. Works on desktop and mobile.
Dev Notes
Reuse the quick-jump function from BL-01.

BL-15 Title
Consistent sidebar status
User Story
As any user, I want the left User Status panel to reflect my real tier and limits, so that I can trust the information.
Acceptance Criteria
1. Switching between free and premium updates badge text and icon instantly.
2. After each search, the remaining count updates in under 250ms.
Dev Notes
Derive sidebar state directly from session store; avoid duplicated counters.

BL-16 Title
Prevent accidental payment in test
User Story
As a tester, I want to be sure I cannot accidentally start a paid subscription, so that testing is safe.
Acceptance Criteria
1. When SAFE_MODE is true, Upgrade to Premium button is disabled with tooltip Disabled in test mode.
2. Attempting to open payment shows an intercept modal explaining test restrictions.
Dev Notes
Server-side enforcement of SAFE_MODE; do not render checkout session in this mode.

BL-17 Title
Results section jump link
User Story
As a user, I want a Jump to results link after a search, so that I can get to outcomes quickly on long pages.
Acceptance Criteria
1. After a successful search, show link Jump to results under Find Food.
2. Clicking the link scrolls to the results container anchor.
Dev Notes
Add id to results container; smooth scroll.

BL-18 Title
Copiable error and support codes
User Story
As a user, I want short, copiable error codes, so that I can share issues with support.
Acceptance Criteria
1. Errors include a short reference like ERR-SRCH-408.
2. Provide Copy error code control.
Dev Notes
Generate stable codes per error category. Do not include PII.

BL-19 Title
Toast on promo apply outcome
User Story
As any user, I want instant feedback when applying a promo, so that I know whether it worked.
Acceptance Criteria
1. On success, show toast such as Promo applied. Premium unlocked or Search counter reset to 3.
2. On failure, show toast Invalid or expired promo code.
Dev Notes
Reuse toast utility from BL-10.

BL-20 Title
Keyboard accessibility polish
User Story
As any user, I want to navigate and apply actions via keyboard, so that the app is accessible.
Acceptance Criteria
1. Tab order: craving, location, Find Food, Have a promo code?, promo input, Apply Code, Jump to results.
2. Enter activates the focused primary action; Escape dismisses toasts.
3. All interactive controls have visible focus and aria labels where appropriate.
Dev Notes
Verify focus outlines, aria-labels, and role attributes.

