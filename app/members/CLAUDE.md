# Members blueprint

The read-mostly members section, open to any logged-in member. It's distinct from the admin-only management page at `/admin/members`. **Admin accounts are excluded everywhere here** (directory, profiles 404, profile links, the "Your profile" menu item); see "Admin accounts aren't readers" in the root CLAUDE.md.

- **`/members/`**: a directory card per member showing picks, review count, average score given, and picked covers.
- **`/members/<id>`**: a profile with the member's picks face-out on a shelf and every review they've written. Each review is compared with the rest of the club's average for that book (`_others_average()` leaves out the member's own score). The "scores more generously/harshly" line is the mean of those per-book differences, shown only beyond a ±0.25 threshold.
- **Display-name edit**: on your own profile, a pencil button beside the name (the shared `data-inline-edit` widget, same icon as the rating card's edit button) swaps the heading for an input. The panel renders already open when the form has errors. It posts `DisplayNameForm` back to `profile()`, a combined GET/POST view like `book_detail()`; POSTing to someone else's profile is a 403. Every member-facing name renders `display_name`, so a rename shows up everywhere without other changes.
- Member names on review cards and "Picked by" link to profiles. The navbar's "Members" link comes here for everyone; admins reach management through the account menu.
