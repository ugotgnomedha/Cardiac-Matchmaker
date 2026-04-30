import argparse
import getpass
from collections.abc import Sequence

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.services.user.user_service import (
	UserAlreadyExistsError,
	UserService,
	UserValidationError,
)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Create a backend user")
	parser.add_argument("email", help="User email")
	parser.add_argument("--password", help="User password. If omitted, you will be prompted securely.")
	parser.add_argument("--superuser", action="store_true", help="Create the user with superuser access.")
	parser.add_argument("--inactive", action="store_true", help="Create the user as inactive.")
	parser.add_argument("--json", action="store_true", help="Print the created user as JSON.")
	return parser


def main(argv: Sequence[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)

	password = args.password or getpass.getpass("Password: ")
	user_service = UserService()

	try:
		db.connect(reuse_if_open=True)
		ensure_migrations_applied()

		user = user_service.create_user(
			{
				"email": args.email,
				"password": password,
				"is_active": not args.inactive,
				"is_superuser": args.superuser,
			}
		)
	except (UserValidationError, UserAlreadyExistsError) as exc:
		parser.exit(status=1, message=f"Error: {exc.detail}\n")
	finally:
		if not db.is_closed():
			db.close()

	if args.json:
		print(user.model_dump_json(indent=2))
	else:
		print(f"Created user {user.email} ({user.id})")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
