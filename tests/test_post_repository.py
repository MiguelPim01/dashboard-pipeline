import unittest
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.domain.entities.enums import SocialNetworkEnum
from src.infra.repositories import post_repository as repo_module


class TestPostRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_module.PostRepository.__abstractmethods__ = frozenset()

    def setUp(self):
        self.repository = repo_module.PostRepository()

    def _mock_db_context(self):
        handler_patch = patch.object(repo_module, "DBConnectionHandler")
        handler_cls = handler_patch.start()
        self.addCleanup(handler_patch.stop)

        db = MagicMock()
        handler_cls.return_value.__enter__.return_value = db
        handler_cls.return_value.__exit__.return_value = None
        return handler_cls, db

    def _mock_joinedload(self):
        loader = MagicMock()
        loader.joinedload.return_value = loader
        joinedload_patch = patch.object(repo_module, "joinedload", return_value=loader)
        joinedload_patch.start()
        self.addCleanup(joinedload_patch.stop)

    def test_fetch_by_date_delegates_to_range_fetch(self):
        sample_day = date(2026, 1, 10)

        with patch.object(
            self.repository,
            "fetch_by_range_and_social_network",
            return_value=["ok"],
        ) as fetch_range:
            result = self.repository.fetch_by_date(sample_day, SocialNetworkEnum.X)

        self.assertEqual(result, ["ok"])
        fetch_range.assert_called_once_with(sample_day, sample_day, SocialNetworkEnum.X)

    def test_fetch_by_range_and_social_network_queries_db_and_filters_subthemes(self):
        _, db = self._mock_db_context()
        self._mock_joinedload()
        query = MagicMock()
        db.session.query.return_value = query
        query.options.return_value = query
        query.filter.return_value = query

        post_allowed = SimpleNamespace(
            subthemes=[SimpleNamespace(themeId="theme-a")],
        )
        post_blocked = SimpleNamespace(
            subthemes=[SimpleNamespace(themeId="theme-z")],
        )
        post_without_subtheme = SimpleNamespace(subthemes=[])

        query.all.return_value = [post_allowed, post_blocked, post_without_subtheme]

        with patch.object(repo_module, "themes_array", ["theme-a", "theme-b"]):
            result = self.repository.fetch_by_range_and_social_network(
                date(2026, 1, 1),
                date(2026, 1, 2),
                SocialNetworkEnum.ALL,
            )

        self.assertEqual(result, [post_allowed])
        db.session.query.assert_called_once_with(repo_module.Post)
        query.all.assert_called_once()

    def test_fetch_by_range_and_social_network_applies_social_network_filter(self):
        _, db = self._mock_db_context()
        self._mock_joinedload()
        query = MagicMock()
        db.session.query.return_value = query
        query.options.return_value = query
        query.filter.return_value = query
        query.all.return_value = [SimpleNamespace(subthemes=[SimpleNamespace(themeId="theme-a")])]

        with patch.object(repo_module, "themes_array", ["theme-a"]):
            self.repository.fetch_by_range_and_social_network(
                date(2026, 1, 1),
                date(2026, 1, 2),
                SocialNetworkEnum.INSTAGRAM,
            )

        # First filter is date range, second filter is social network.
        self.assertEqual(query.filter.call_count, 2)

    def test_delete_removes_post_and_commits(self):
        _, db = self._mock_db_context()
        query = MagicMock()
        db.session.query.return_value = query
        query.filter.return_value = query
        post = SimpleNamespace(id="p1")
        query.first.return_value = post

        post_id = str(uuid.uuid4())
        self.repository.delete(post_id)

        db.session.query.assert_called_once_with(repo_module.Post)
        db.session.delete.assert_called_once_with(post)
        db.session.commit.assert_called_once()

    def test_delete_raises_for_invalid_uuid(self):
        _, db = self._mock_db_context()

        with self.assertRaises(ValueError) as context:
            self.repository.delete("invalid-uuid")

        self.assertIn("Formato de ID inválido", str(context.exception))
        db.session.query.assert_not_called()

    def test_delete_raises_when_post_not_found(self):
        _, db = self._mock_db_context()
        query = MagicMock()
        db.session.query.return_value = query
        query.filter.return_value = query
        query.first.return_value = None

        post_id = str(uuid.uuid4())
        with self.assertRaises(ValueError) as context:
            self.repository.delete(post_id)

        self.assertIn("não encontrado", str(context.exception))
        db.session.delete.assert_not_called()
        db.session.commit.assert_not_called()

    def test_edit_updates_fields_and_commits(self):
        _, db = self._mock_db_context()
        query = MagicMock()
        db.session.query.return_value = query
        query.filter.return_value = query
        post = SimpleNamespace(message="old", likes=1)
        query.first.return_value = post

        self.repository.edit("post-id", {"message": "new", "likes": 2})

        self.assertEqual(post.message, "new")
        self.assertEqual(post.likes, 2)
        db.session.commit.assert_called_once()

    def test_edit_raises_when_post_not_found(self):
        _, db = self._mock_db_context()
        query = MagicMock()
        db.session.query.return_value = query
        query.filter.return_value = query
        query.first.return_value = None

        with self.assertRaises(ValueError) as context:
            self.repository.edit("post-id", {"message": "new"})

        self.assertIn("não encontrado", str(context.exception))
        db.session.commit.assert_not_called()

    def test_edit_raises_for_invalid_field(self):
        _, db = self._mock_db_context()
        query = MagicMock()
        db.session.query.return_value = query
        query.filter.return_value = query
        query.first.return_value = SimpleNamespace(message="old")

        with self.assertRaises(AttributeError) as context:
            self.repository.edit("post-id", {"nonexistent_field": "value"})

        self.assertIn("não existe", str(context.exception))
        db.session.commit.assert_not_called()

    def test_get_by_id_uses_db_and_returns_post(self):
        _, db = self._mock_db_context()
        self._mock_joinedload()
        query = MagicMock()
        db.session.query.return_value = query
        query.options.return_value = query
        query.filter.return_value = query
        expected_post = SimpleNamespace(id="post-1")
        query.first.return_value = expected_post

        result = self.repository.get_by_id("post-1")

        self.assertIs(result, expected_post)
        db.session.query.assert_called_once_with(repo_module.Post)
        query.first.assert_called_once()


if __name__ == "__main__":
    unittest.main()
