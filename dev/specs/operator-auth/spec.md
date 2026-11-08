# Специфікація operator-auth

## Призначення

<!-- Purpose -->

Домен відповідає за захист інтерфейсу оператора при публічному розгортанні.
Захист опційний: локально інтерфейс відкритий, на сервері вмикається однією змінною оточення.

## Вимоги

<!-- Requirements -->

### Вимога: Basic Auth за паролем

<!-- Requirement -->

Якщо `OPERATOR_PASSWORD` непорожній, кожен запит до `/ui` і `/ui/...` МАЄ вимагати HTTP Basic Auth з цим паролем (логін довільний); без коректного пароля — `401` із заголовком `WWW-Authenticate: Basic`.
Якщо `OPERATOR_PASSWORD` порожній, інтерфейс НЕ МАЄ вимагати автентифікації.
Захист НЕ МАЄ поширюватися на `/health` і `/webhooks/helpdesk`.

#### Сценарій: Без пароля відмова

<!-- Scenario -->

- ДАНО `OPERATOR_PASSWORD=s3cret`
- ЯКЩО відкрити `/ui` без заголовка `Authorization`
- ТО відповідь `401` із `WWW-Authenticate: Basic`

#### Сценарій: З паролем доступ

<!-- Scenario -->

- ДАНО `OPERATOR_PASSWORD=s3cret`
- ЯКЩО відкрити `/ui` з Basic Auth `operator:s3cret`
- ТО відповідь `200`

#### Сценарій: Захист вимкнено

<!-- Scenario -->

- ДАНО порожній `OPERATOR_PASSWORD`
- ЯКЩО відкрити `/ui` без заголовка `Authorization`
- ТО відповідь `200`

#### Сценарій: Вебхук без автентифікації

<!-- Scenario -->

- ДАНО `OPERATOR_PASSWORD=s3cret`
- ЯКЩО хелпдеск надсилає валідну подію на `/webhooks/helpdesk` без `Authorization`
- ТО відповідь `202`
