# Ecommerce Product Planning Document

## Project Name
East Africa Ecommerce Platform

## Project Summary
East Africa Ecommerce Platform is a full-stack ecommerce application focused on women's fashion, accessories, jewelry, shoes, perfume, and lingerie for the East African market. The platform combines a Django backend, admin-managed inventory, a customer shopping flow, responsive pages, and payment-ready architecture.

## Problem Statement
Small fashion businesses and women-led retail brands need a storefront that is easier to manage than social-media-only selling and more region-aware than generic ecommerce templates. This project addresses that gap by providing a product catalog, cart flow, currency-aware pricing, and an admin-managed inventory workflow that can be extended with African payment providers.

## Project Goal
Build a polished ecommerce platform where shoppers can browse products, add items to cart, view totals in supported currencies, choose a payment method, and complete a scalable checkout flow while admins securely manage products and media.

## Target Audience
- Women shoppers across East Africa
- Boutique owners and fashion entrepreneurs
- Small businesses that need a manageable storefront and inventory workflow

## Business Value
- Gives local fashion sellers a modern digital storefront
- Supports region-aware shopping through currency conversion and payment expansion
- Demonstrates a realistic full-stack commerce workflow for retail operations

## Core Objectives
- Deliver a working full-stack shopping experience
- Keep inventory and catalog data controlled through the database and admin panel
- Provide a responsive and branded customer experience
- Support product documentation, planning, and delivery tracking
- Keep payment integrations modular for provider expansion

## In Scope
- Product catalog backed by database records
- Inventory page with size, quantity, currency, and payment method selectors
- Cart add, update, and remove flows
- Admin product and image management
- Responsive user-facing pages
- Project documentation and delivery tracking

## Out Of Scope For Initial Submission
- Marketplace multi-vendor onboarding
- Full order history dashboard
- Production payment settlement
- Recommendation engine or personalization
- Advanced analytics or reporting dashboards

## Current Implementation Snapshot

### Completed
- Home, About, Catalog, Inventory, and Cart pages are implemented
- Catalog uses database products and linked product images
- Admin can manage categories, products, product images, carts, and cart items
- Cart totals are calculated correctly on the server
- Currency conversion is available for USD, EUR, KES, and UGX
- Payment method selection is available for MTN, Airtel, and WorldRemit
- Product pricing is varied instead of a single flat price
- Inventory sizes are standardized to EU sizes 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, and 54
- Admin Sign In / Admin Panel access is exposed in the site navigation
- Shopper authentication is implemented (signup/login/logout)
- Guest cart items merge into authenticated user cart after signup/login
- Contact inquiry communication flow is implemented (admin persistence plus SMTP email delivery)
- Checkout captures orders and shows payment-verification instructions with admin-managed payment status
- Payment sandbox integration is implemented end-to-end
- Inventory quantity control is implemented via stock_quantity with checkout stock validation and decrement
- README contains project summary, tech stack, page map, and local run guide
- Phone and tablet responsive QA is completed for all storefront pages
- Screenshots in `images/screenshots/`; interactive demo deck at `docs/demo-presentation.html`
- Initial delivery complete (ongoing improvements via Git)

### Remaining
- None. All planned scope is delivered.

## User Types

### Shopper
- Browses products
- Adds items to cart
- Updates quantity and size choices
- Chooses currency and payment method
- Completes checkout flow

### Admin
- Adds products
- Edits products
- Links images to products
- Deletes outdated inventory
- Manages categories and product metadata

## Epics
- Shopper Authentication
- Product Browsing And Catalog
- Cart And Checkout
- Payment Integration
- Admin Inventory Management
- QA, Documentation, And Submission

## User Stories

### Shopper Authentication
- As a shopper, I want to sign up so that I can create an account and keep my shopping activity.
- As a shopper, I want to log in so that I can access my cart and future order history.
- As a shopper, I want to log out securely so that my account stays protected on shared devices.

### Product Browsing And Catalog
- As a shopper, I want to browse products with images, prices, and descriptions so that I can compare items quickly.
- As a shopper, I want to open product details so that I can see more than one product image before buying.
- As a shopper, I want the catalog to only show real inventory items so that deleted products do not reappear.

### Cart And Checkout
- As a shopper, I want to add a product with quantity and size so that I can prepare an accurate order.
- As a shopper, I want to update or remove items in my cart so that I can control my order before checkout.
- As a shopper, I want to view totals in my preferred currency so that pricing is easier to understand.
- As a shopper, I want to select a payment method so that checkout matches regional payment expectations.
- As a shopper, I want checkout to generate an order reference and clear next-step payment instructions so that I know how to complete my order.

### Payment Integration
- As a shopper, I want at least one payment method to reach a real sandbox flow so that checkout feels complete.
- As the business owner, I want payment integration to be modular so that more providers can be added later.

### Admin Inventory Management
- As an admin, I want to add products and images so that the storefront stays current.
- As an admin, I want to edit product details and prices so that catalog information stays accurate.
- As an admin, I want deleted products removed from the customer catalog so that customers only see active items.

### QA, Documentation, And Submission
- As a product owner, I want clear documentation so that stakeholders understand project scope and architecture.
- As a product owner, I want a task board with clear progress states so work is easy to track and review.
- As a delivery team, we want final QA and demo assets so releases are ready for handoff.

## Functional Requirements
- The system must display products from database records, not loose image files.
- The system must support add-to-cart, update-cart, and remove-cart actions.
- The system must display converted prices in USD, EUR, KES, and UGX.
- The system must allow users to choose MTN, Airtel, or WorldRemit as a checkout preference.
- The admin panel must allow secure inventory management.
- The project must include clear documentation and a trackable delivery workflow.

## Non-Functional Requirements
- Pages should remain responsive on desktop, tablet, and mobile layouts.
- Pricing calculations should be consistent and server-side validated.
- Project structure should stay maintainable across backend, frontend, and payments services.
- User-facing flows should remain understandable and visually consistent.

## Success Criteria
- A shopper can browse, add to cart, update quantities, and view converted totals.
- An admin can manage catalog inventory through Django admin.
- Checkout captures orders with automated Pesapal gateway handoff plus clear status tracking.
- Authentication exists for shopper accounts.
- Documentation, Trello tracking, and final QA artifacts are complete.

## Recommended Trello Updates As Of 2026-05-06 — Final Submission Ready

### Move To Done
- Shopper Authentication
- Communication And Notifications
- Cart Calculations And Checkout Preferences
- Admin Inventory Management
- Catalog Experience
- Inventory Shopping Flow
- Order Capture And Payment Processing
- Responsive QA

### Move To Done
- Submission Packaging
- Presentation Assets
- README And Project Documentation
- Release Validation Snapshot
- Payment Sandbox Integration

### Add Card: Release Validation Snapshot
Checklist:
- Run Django system check
- Run Django test suite
- Build frontend production bundle
- Note exchange-rate API fallback warning behavior
- Record validation date in project notes

### Add Card: Submission Packaging
Checklist:
- Confirm live Railway URL in README
- Confirm Trello board link in README
- Confirm GitHub repository link in README
- Prepare final screenshots or demo assets
- Prepare final submission document or cover sheet if required

## Recommended Trello Board Structure

### Lists
- Backlog
- Ready Next
- In Progress
- Review And QA
- Done
- Demo Assets

## Trello Cards And Checklists

### Card: Project Setup And Environment
Checklist:
- Confirm backend virtual environment works
- Confirm Django migrations run cleanly
- Confirm frontend dependencies install
- Confirm payments service dependencies install
- Verify local run commands in README
- Verify .env.example and .env usage

### Card: Product Data Model And Seed Workflow
Checklist:
- Review product model fields
- Review product image model relationships
- Seed products from workspace images
- Standardize sizes to XS through XXL
- Confirm varied pricing logic
- Remove obsolete legacy seed data

### Card: Catalog Experience
Checklist:
- Show database-backed catalog cards
- Display product description and price on each card
- Open detail modal with second image when available
- Ensure deleted products do not appear in catalog
- Confirm empty-image products are skipped safely
- QA desktop and mobile catalog layout

### Card: Inventory Shopping Flow
Checklist:
- Display product list with price and description
- Add size selector
- Add quantity selector
- Add currency selector
- Add payment method selector
- Auto-submit selector changes where appropriate
- Verify add-to-cart action from inventory page

### Card: Cart Calculations And Checkout Preferences
Checklist:
- Display cart items in table view
- Support quantity updates
- Support remove item action
- Calculate line totals on server
- Calculate grand total on server
- Show selected currency and payment method
- Verify live rate fallback behavior

### Card: Shopper Authentication
Checklist:
- Create signup page and form
- Create login page and form
- Create logout action
- Link auth views in main navigation
- Attach cart behavior to authenticated user when available
- Test invalid login and success login flows

### Card: Order Capture And Payment Processing
Checklist:
- Capture checkout form into Order and OrderItem records
- Generate order reference for shopper confirmation
- Initiate Pesapal gateway handoff from checkout when selected
- Show initial Pending payment status to shopper
- Confirm callback updates status to Payment confirmed or Payment failed
- Document automated and method-specific payment flows in README

### Card: Release Validation Snapshot
Checklist:
- Run Django system check
- Run Django test suite
- Build frontend production bundle
- Note exchange-rate API fallback warning behavior
- Record validation date in project notes

### Card: Submission Packaging
Checklist:
- Confirm live Railway URL in README
- Confirm Trello board link in README
- Confirm GitHub repository link in README
- Prepare final screenshots or demo assets
- Prepare final submission document or cover sheet if required

### Card: Payment Sandbox Integration
Checklist:
- Choose primary provider for sandbox demo
- Confirm backend payment endpoint contract
- Confirm payments microservice route exists
- Implement initiation flow from checkout
- Handle success response state
- Handle failure response state
- Document sandbox run instructions

### Card: Communication And Notifications
Checklist:
- Choose communication method for submission scope
- Add contact or confirmation email workflow
- Configure development email backend
- Add user-facing success message
- Document configuration steps

### Card: Admin Inventory Management
Checklist:
- Register product models in admin
- Register cart models in admin
- Confirm product image inline editing
- Verify add product flow
- Verify edit product flow
- Verify delete product flow
- Verify customer catalog updates after admin changes

### Card: Responsive QA
Checklist:
- Test home page on mobile
- Test about page on mobile
- Test catalog modal on mobile
- Test inventory controls on mobile
- Test cart table and totals on mobile
- Test admin sign-in path on mobile
- Fix any spacing or overflow issues

### Card: README And Project Documentation
Checklist:
- Confirm project description
- Confirm industry context and target audience
- Confirm elevator pitch
- Confirm page and feature map
- Add final GitHub repository link
- Link planning document from README
- Confirm local setup instructions are current

### Card: Presentation Assets
Checklist:
- Capture screenshots of key pages
- Prepare short demo walkthrough outline
- Confirm Trello board is organized
- Confirm README is submission-ready
- Confirm repository is clean enough for review
- Prepare talking points for implemented vs planned work

## Final Trello Placement As Of 2026-05-06 — Submitted

### Done
- Project Setup And Environment
- Product Data Model And Seed Workflow
- Catalog Experience
- Inventory Shopping Flow
- Cart Calculations And Checkout Preferences
- Admin Inventory Management
- Shopper Authentication
- Communication And Notifications
- Order Capture And Payment Processing
- Payment Sandbox Integration
- Responsive QA
- README And Project Documentation
- Presentation Assets
- Release Validation Snapshot
- Submission Packaging

## Priority Order — All Delivered
1. ✓ Submission Packaging
2. ✓ Presentation Assets
3. ✓ README And Project Documentation
4. ✓ Release Validation Snapshot
5. ✓ Payment Sandbox Integration

## Definition Of Done For Each Trello Card
- Feature works in the local environment
- UI path is reachable from the application
- Edge cases were manually tested
- Any README or setup changes are documented
- Card checklist is fully completed before moving to Done

## Suggested Labels
- Frontend
- Backend
- Database
- Payments
- Auth
- QA
- Documentation
- Delivery

## Weekly Tracking Format

### This Week
- Move only active implementation cards into In Progress
- Keep documentation card updated alongside code changes
- Capture blockers as comments on the relevant Trello card

### End Of Week Review
- Move tested items to Review And QA
- Move approved items to Done
- Update README and submission assets if project scope changed

## How To Use This Document With Trello
1. Create the six recommended Trello lists.
2. Create each Trello card using the exact card titles in this document.
3. Copy the checklist items under each card into a Trello checklist.
4. Apply labels for Frontend, Backend, Payments, QA, or Documentation.
5. Use the Priority Order section to decide what moves from Backlog into Ready Next and In Progress.

## Short Delivery Narrative
This project delivers a complete full-stack ecommerce platform. Shoppers can browse real products, create accounts, manage a cart, view prices in multiple currencies, and complete checkout with an order reference and integrated payment handoff. Admins manage inventory, monitor payment status updates, and receive contact inquiries via email. Responsive QA is complete across all storefront pages. All planned cards are done.