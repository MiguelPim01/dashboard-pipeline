import uuid
from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy.orm import joinedload
from sqlalchemy import text

from src.config.settings import get_settings
from src.domain.entities.enums import SocialNetworkEnum
from src.domain.entities.post import Post
from src.domain.entities.subtheme import Subtheme
from src.domain.repositories.post_repository_interface import IPostRepository
from src.infra.db.connection import DBConnectionHandler

settings = get_settings()
themes_array = settings.THEMES_ARRAY.split(",")


class PostRepository(IPostRepository):
    def fetch_by_date(self, day: date, social_network: SocialNetworkEnum) -> List[Post]:
        return self.fetch_by_range_and_social_network(day, day, social_network)

    def fetch_by_range_and_social_network(
        self, start_date: date, end_date: date, social_network: SocialNetworkEnum
    ) -> List[Post]:
        # Ajusta para 00:00 no início e 23:59:59.999999 no final
        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)

        with DBConnectionHandler() as db:
            query = (
                db.session.query(Post)
                .options(joinedload(Post.subthemes).joinedload(Subtheme.theme))
                .filter(
                    Post.time >= start_datetime,
                    Post.time <= end_datetime,
                )
            )

            # Se não for ALL, filtrar por rede social específica
            if social_network != SocialNetworkEnum.ALL:
                query = query.filter(Post.socialNetwork == social_network)

            posts = query.all()

        filtered_posts = []
        for post in posts:
            if post.subthemes:
                for subtheme in post.subthemes:
                    if subtheme.themeId in themes_array:
                        filtered_posts.append(post)
                        break

        return filtered_posts

    def delete(self, post_id: str) -> None:
        with DBConnectionHandler() as db:
            try:
                # Converter string para UUID
                post_uuid = uuid.UUID(post_id)
            except ValueError as exc:
                raise ValueError("Formato de ID inválido") from exc

            # Consulta com CAST explícito e filtro isRelevant
            post = (
                db.session.query(Post)
                .filter(
                    Post.id == str(post_uuid), Post.isRelevant == True
                )  # Converter UUID para string
                .first()
            )

            if not post:
                raise ValueError(f"Post {post_id} não encontrado")

            db.session.delete(post)
            db.session.commit()

    def edit(self, post_id: str, updates: dict) -> None:
        with DBConnectionHandler() as db:
            post = (
                db.session.query(Post).filter(Post.id == post_id, Post.isRelevant == True).first()
            )
            if not post:
                raise ValueError(f"Post {post_id} não encontrado")

            for key, value in updates.items():
                if not hasattr(post, key):
                    raise AttributeError(f"Campo {key} não existe no Post")
                setattr(post, key, value)

            db.session.commit()

    def get_by_id(self, post_id: str) -> Optional[Post]:
        with DBConnectionHandler() as db:
            post = (
                db.session.query(Post)
                .options(joinedload(Post.subthemes).joinedload(Subtheme.theme))
                .filter(Post.id == post_id, Post.isRelevant == True)
                .first()
            )
            return post
