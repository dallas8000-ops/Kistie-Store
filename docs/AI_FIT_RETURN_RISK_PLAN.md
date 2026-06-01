# AI Fit and Return-Risk Recommender

## Goal

Increase conversion and reduce returns by helping shoppers choose the right product, size, and bundle before checkout.

This feature should be built on top of the existing Kistie Store sizing and shopping data:

- Product records already store EU size ranges.
- Cart and order records already capture selected size and quantity.
- The app already has a basic `api/size-recommend/` endpoint, which can be extended instead of replaced.

## Why this feature first

This is the highest-value AI addition for the store because it has a direct business link:

- fewer wrong-size purchases
- fewer support messages about fit
- higher checkout confidence
- better bundle acceptance when the recommender suggests matching items

## Feature scope

### Shopper flow

The recommender should ask a short intake form with fields such as:

- height
- usual size
- fit preference: snug / regular / relaxed
- occasion: office / casual / party / wedding / travel
- product category preference
- optional bust / waist / hips measurements

Then it should return:

- a primary product recommendation
- a suggested size
- one fallback size
- a simple fit confidence label
- a short explanation in plain language
- optional bundle suggestions for the same occasion

### Staff flow

Staff should be able to see which products or categories are causing high fit-risk scores so they can:

- adjust size guidance
- improve product descriptions
- reorder the most reliable sizes
- promote bundles for the same occasion

## Data already available

The current app already exposes the minimum data needed for a first version:

- `inventory.Product.sizes`
- `inventory.Product.color`
- `inventory.Product.category`
- `cart.CartItem.size`
- `cart.OrderItem.size`
- `cart.Order.status`
- product images and descriptions for ranking and explanation text

That means the first version can be rule-based with optional AI wording, and later versions can learn from real order history.

## Suggested implementation shape

### Backend

Add a new endpoint or extend the current sizing endpoint with fit metadata.

Recommended path:

- keep `POST /api/size-recommend/` for basic size selection
- add `POST /api/fit-recommend/` for product-level fit guidance

The fit endpoint should accept:

- `bust`, `waist`, `hips`
- `height`
- `usual_size`
- `fit_preference`
- `occasion`
- `product_id` or `category_id`

And return:

- `recommended_size`
- `fit_confidence`
- `return_risk`
- `why`
- `bundle_suggestions`

### Scoring logic

Start simple and deterministic:

1. Compare body measurements to the EU size table.
2. Penalize products whose available size list is sparse.
3. Penalize missing measurements or unknown size preference.
4. Reward products with strong historical purchase/return signals once those are available.
5. Convert the final score into `low`, `medium`, or `high` return risk.

This keeps the first release explainable and cheap.

### AI usage

Use AI only where it adds value:

- turn the score into a short shopper-friendly explanation
- generate bundle copy such as “complete the look” suggestions
- summarize why a product is a better fit for a specific occasion

Do not use AI as the primary decision-maker in version 1.

## Frontend placement

Add the recommender where it can affect purchase decisions:

- product detail modal/page
- inventory page quick-view panel
- cart sidebar before checkout

The best default placement is product detail + quick-view, because that is where fit questions are strongest.

## Success metrics

Track these after launch:

- more add-to-cart actions from product detail views
- fewer abandoned carts on size-sensitive items
- fewer manual fit questions in contact support
- higher bundle attachment rate
- lower percentage of orders with size-related complaints

## 30-day build plan

### Week 1

- define endpoint contract
- wire product and order data into a fit scoring service
- return size + risk labels for one product at a time

### Week 2

- add the recommender UI to product detail and quick-view flows
- add a small bundle suggestion panel
- add tests for valid/invalid measurements

### Week 3

- add analytics events for view, recommendation accepted, and checkout conversion
- add admin-facing fit-risk summary for products

### Week 4

- refine scoring thresholds
- add shopper-facing copy improvements
- document the feature in the README or product notes

## Recommended first version

Build the first version as a hybrid system:

- rule-based fit scoring for accuracy and speed
- optional LLM wording for explanation text
- no dependence on large training data

That gives the app a real commercial feature quickly, while keeping the path open for more advanced personalization later.