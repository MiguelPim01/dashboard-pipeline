from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date

from src.domain.entities.enums import SocialNetworkEnum
from src.domain.entities.post import Post


class IPostRepository(ABC):
    """
    Interface (abstract base class) for PostRepository implementations.
    Defines the contract for retrieving Post entities from the data source.
    """

    @abstractmethod
    def fetch_by_date(self, day: date, social_network: SocialNetworkEnum) -> List[Post]:
        """
        Retrieves all posts that were created on a specific day.

        Args:
            day (date): The day for which to retrieve posts.
            social_network (SocialNetworkEnum): The social network to filter by.

        Returns:
            List[Post]: A list of posts matching the given date.
        """
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    def fetch_by_range_and_social_network(
        self, start_date: date, end_date: date, social_network: SocialNetworkEnum
    ) -> List[Post]:
        """
        Retrieves posts filtered by a specified time range and social network.

        Args:
            start_date (date): The start date of the time range.
            end_date (date): The end date of the time range.
            social_network (SocialNetworkEnum): The social network to filter by.

        Returns:
            List[Post]: A list of posts matching the criteria.
        """
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    def delete(self, post_id: str) -> bool:
        """
        Deletes a post by its ID.

        Args:
            post_id (str): The ID of the post to delete.

        Returns:
            bool: True if one post has deleted

        Raises:
            ValueError: If the post is not found.
        """
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    def get_by_id(self, post_id: str) -> Post:
        """
        Retrieves a post by its ID.

        Args:
            post_id (str): The ID of the post to retrieve.

        Returns:
            Post: The post with the specified ID.

        Raises:
            ValueError: If the post is not found.
        """
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    def edit(self, post_id: str, updates: dict) -> None:
        """
        Edita um post existente com os valores fornecidos.

        Args:
            post_id (str): ID do post a ser editado
            updates (dict): Dicionário com campos e novos valores

        Raises:
            ValueError: Se o post não for encontrado
            AttributeError: Se tentar editar campo inexistente
        """
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    def deactivate_user_posts(self, user_id: str) -> List[Post]:
        """
        Define isRelevant=False para todos os posts do usuário.
        Retorna a lista de posts alterados.

        Args:
            user_id (str): ID do usuário cujos posts serão desativados

        Returns:
            List[Post]: Lista de posts que foram desativados

        Raises:
            ValueError: Se o usuário não for encontrado ou não tiver posts
        """
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    def create_with_subthemes(self, post_data: dict, subtheme_ids: List[str]) -> Post:
        """
        Cria um novo post com subtemas associados.
        """
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    def update_pa_feedback(self, post_id: str, pa_feedback: Optional[bool]) -> bool:
        """
        Atualiza o feedback de ponto de atenção (PA) de um post.

        Args:
            post_id (str): ID do post a ser atualizado
            pa_feedback (Optional[bool]): Novo valor do feedback de PA
                - True: Post confirmado como ponto de atenção
                - False: Post rejeitado como ponto de atenção
                - None: Remover feedback (voltar ao estado neutro)

        Returns:
            bool: True se a atualização foi bem-sucedida, False caso contrário

        Raises:
            ValueError: Se o post não for encontrado
        """
        raise NotImplementedError("Method not implemented")
