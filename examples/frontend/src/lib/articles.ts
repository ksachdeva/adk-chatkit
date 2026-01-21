export type Article = {
  id: string;
  title: string;
  summary: string;
  content: string;
  author?: string;
  date: string;
  category: string;
  tags?: string[];
  emoji: string;
  heroImageUrl?: string;
};

type ArticlesResponse = {
  articles: Article[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchArticles(): Promise<Article[]> {
  const response = await fetch(`${API_BASE_URL}/news/articles`);
  if (!response.ok) {
    throw new Error(`Failed to fetch articles: ${response.statusText}`);
  }
  const data: ArticlesResponse = await response.json();
  return data.articles;
}

export async function fetchArticle(id: string): Promise<Article> {
  const response = await fetch(`${API_BASE_URL}/news/articles/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch article ${id}: ${response.statusText}`);
  }
  const article: Article = await response.json();
  return article;
}

export function formatArticleDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}
