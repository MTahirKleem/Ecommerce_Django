# Design: Local MongoDB for ShopAi

## Goal
Replace SQLite with local MongoDB database `ecommerce`.

## Approach
Official **Django MongoDB Backend 5.2** (requires Django 5.2 LTS).

## Connection
- Host: `mongodb://127.0.0.1:27017`
- Database name: `ecommerce`
- Engine: `django_mongodb_backend`

## Changes
1. Install `django-mongodb-backend==5.2.*`
2. Update `DATABASES` + MongoDB-required settings (`DEFAULT_AUTO_FIELD`, `MIGRATION_MODULES`)
3. Update dependency pin file
4. Run `migrate` against MongoDB

## Out of scope
- Data migration from existing `db.sqlite3`
- Atlas / auth-enabled MongoDB URIs

## Implementation notes
- Django upgraded 4.2 → 5.2.17 for official backend support
- Contrib apps use `ShopAi.apps.Mongo*Config` + `mongo_migrations/`
- App migrations reset to a single ObjectId-based `0001_initial`
- `paypal.standard.ipn` removed from `INSTALLED_APPS` (AutoField incompatible; checkout uses PayPal JS)
