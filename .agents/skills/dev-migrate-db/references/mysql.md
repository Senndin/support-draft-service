# Example: a MySQL migration pair

An illustration of a forward/rollback pair in one specific dialect. It is not a rule for every project -- follow the dialect and conventions the project actually documents.

The pair below adds a `user_addresses` table with an index on its foreign key, and removes both again.

## Forward Migration (Up)

```sql
START TRANSACTION;

CREATE TABLE user_addresses (
  id INT NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  PRIMARY KEY (id)
);

ALTER TABLE user_addresses ADD INDEX idx_user_id (user_id);

COMMIT;
```

## Rollback Migration (Down)

```sql
START TRANSACTION;

ALTER TABLE user_addresses DROP INDEX idx_user_id;

DROP TABLE IF EXISTS user_addresses;

COMMIT;
```

## Dump syntax omitted from both scripts

A MySQL dump of the same table would carry extra syntax that does not belong in a migration:

- auto-generated dump comments, such as `/*!40101 SET @saved_cs_client = @@character_set_client */`;
- storage engine declarations, such as `ENGINE=InnoDB`;
- default character set and collation definitions, such as `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`;
- internal auto-increment starting values, such as `AUTO_INCREMENT=6`.
