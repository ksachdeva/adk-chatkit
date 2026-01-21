import clsx from "clsx";
import { ChevronLeftIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useNavigate, useParams } from "react-router-dom";
import remarkGfm from "remark-gfm";

import { fetchArticle, fetchArticles, formatArticleDate } from "../../lib/articles";
import type { Article } from "../../lib/articles";
import "./NewsroomPanel.css";

const INITIAL_ARTICLES_COUNT = 9;

export function NewsroomPanel() {
  const { articleId } = useParams<{ articleId?: string }>();
  const navigate = useNavigate();
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [isLoadingArticles, setIsLoadingArticles] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Load articles on mount
  useEffect(() => {
    let cancelled = false;
    setIsLoadingArticles(true);
    fetchArticles()
      .then((data) => {
        if (!cancelled) {
          setArticles(data.slice(0, INITIAL_ARTICLES_COUNT));
          setIsLoadingArticles(false);
        }
      })
      .catch((error) => {
        console.error("Failed to fetch articles:", error);
        if (!cancelled) {
          setIsLoadingArticles(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Load article details when articleId changes
  useEffect(() => {
    if (!articleId || articleId === "featured") {
      setSelectedArticle(null);
      return;
    }

    let cancelled = false;
    setIsLoadingDetail(true);

    fetchArticle(articleId)
      .then((article) => {
        if (!cancelled) {
          setSelectedArticle(article);
          setIsLoadingDetail(false);
        }
      })
      .catch((error) => {
        console.error(`Failed to fetch article ${articleId}:`, error);
        if (!cancelled) {
          setIsLoadingDetail(false);
          setSelectedArticle(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [articleId]);

  const handleArticleClick = useCallback(
    (id: string) => {
      navigate(`/news-guide/${id}`);
    },
    [navigate]
  );

  const handleBackClick = useCallback(() => {
    navigate("/news-guide");
  }, [navigate]);

  const showingDetail = !!selectedArticle;

  return (
    <div className="h-full w-full overflow-y-auto bg-white dark:bg-neutral-900">
      <div className="mx-auto max-w-7xl px-6 py-12">
        {showingDetail ? (
          <ArticleDetail
            article={selectedArticle}
            isLoading={isLoadingDetail}
            onBackClick={handleBackClick}
          />
        ) : (
          <LandingGrid
            articles={articles}
            isLoading={isLoadingArticles}
            onArticleClick={handleArticleClick}
          />
        )}
      </div>
    </div>
  );
}

type LandingGridProps = {
  articles: Article[];
  isLoading: boolean;
  onArticleClick: (id: string) => void;
};

function LandingGrid({ articles, isLoading, onArticleClick }: LandingGridProps) {
  const [featuredArticle, ...secondaryArticles] = articles;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-neutral-500">Loading articles...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-8 text-4xl font-semibold text-neutral-900 dark:text-white">
        Foxhollow Newsroom
      </h1>

      {featuredArticle && (
        <div className="mb-12">
          <FeaturedArticleCard article={featuredArticle} onClick={onArticleClick} />
        </div>
      )}

      {secondaryArticles.length > 0 && (
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {secondaryArticles.map((article) => (
            <SecondaryArticleCard key={article.id} article={article} onClick={onArticleClick} />
          ))}
        </div>
      )}
    </div>
  );
}

type FeaturedArticleCardProps = {
  article: Article;
  onClick: (id: string) => void;
};

function FeaturedArticleCard({ article, onClick }: FeaturedArticleCardProps) {
  const handleClick = useCallback(() => {
    onClick(article.id);
  }, [onClick, article.id]);

  const formattedDate = useMemo(() => formatArticleDate(article.date), [article.date]);

  return (
    <button
      onClick={handleClick}
      className="group w-full cursor-pointer overflow-hidden rounded-sm bg-neutral-50 text-left transition-colors hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
    >
      <div className="grid gap-6 p-8 md:grid-cols-2">
        <div className="flex flex-col">
          <div className="mb-3 flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
            <time dateTime={article.date}>{formattedDate}</time>
            <span>·</span>
            <span className="capitalize">{article.category}</span>
          </div>
          <h2 className="mb-4 text-3xl font-semibold leading-tight text-neutral-900 transition-colors group-hover:text-[#ff5f42] dark:text-white dark:group-hover:text-[#ff5f42]">
            {article.title}
          </h2>
          <p className="mb-4 line-clamp-3 text-neutral-700 dark:text-neutral-300">
            {article.summary}
          </p>
          {article.author && (
            <div className="text-sm text-neutral-600 dark:text-neutral-400">By {article.author}</div>
          )}
          {article.tags && article.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {article.tags.slice(0, 4).map((tag) => (
                <span
                  key={tag}
                  className={clsx("tag", `tag-${tag.toLowerCase().replace(/\s+/g, "-")}`)}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center justify-center">
          <div className="text-6xl opacity-20">{article.emoji}</div>
        </div>
      </div>
    </button>
  );
}

type SecondaryArticleCardProps = {
  article: Article;
  onClick: (id: string) => void;
};

function SecondaryArticleCard({ article, onClick }: SecondaryArticleCardProps) {
  const handleClick = useCallback(() => {
    onClick(article.id);
  }, [onClick, article.id]);

  const formattedDate = useMemo(() => formatArticleDate(article.date), [article.date]);

  return (
    <button
      onClick={handleClick}
      className="group flex cursor-pointer flex-col overflow-hidden rounded-sm bg-neutral-50 text-left transition-colors hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
    >
      <div className="flex h-32 items-center justify-center bg-neutral-100 dark:bg-neutral-700">
        <div className="text-5xl opacity-30">{article.emoji}</div>
      </div>
      <div className="flex flex-1 flex-col p-6">
        <div className="mb-2 flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <time dateTime={article.date}>{formattedDate}</time>
          <span>·</span>
          <span className="capitalize">{article.category}</span>
        </div>
        <h3 className="mb-3 text-xl font-semibold leading-snug text-neutral-900 transition-colors group-hover:text-[#ff5f42] dark:text-white dark:group-hover:text-[#ff5f42]">
          {article.title}
        </h3>
        <p className="mb-3 line-clamp-2 flex-1 text-sm text-neutral-700 dark:text-neutral-300">
          {article.summary}
        </p>
        {article.tags && article.tags.length > 0 && (
          <div className="mt-auto flex flex-wrap gap-1.5">
            {article.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className={clsx("tag tag-sm", `tag-${tag.toLowerCase().replace(/\s+/g, "-")}`)}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  );
}

type ArticleDetailProps = {
  article: Article | null;
  isLoading: boolean;
  onBackClick: () => void;
};

function ArticleDetail({ article, isLoading, onBackClick }: ArticleDetailProps) {
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-neutral-500">Loading article...</div>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-neutral-500">Article not found</div>
      </div>
    );
  }

  const formattedDate = formatArticleDate(article.date);

  return (
    <div className="mx-auto max-w-3xl">
      <button
        onClick={onBackClick}
        className="mb-6 flex items-center gap-2 text-sm text-neutral-600 transition-colors hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-white"
      >
        <ChevronLeftIcon className="h-4 w-4" />
        Back to newsroom
      </button>

      <article className="prose prose-neutral dark:prose-invert max-w-none">
        <div className="mb-6 flex items-center gap-3">
          <div className="text-4xl">{article.emoji}</div>
          <div className="flex-1">
            <div className="mb-1 flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
              <time dateTime={article.date}>{formattedDate}</time>
              <span>·</span>
              <span className="capitalize">{article.category}</span>
            </div>
            {article.author && (
              <div className="text-sm text-neutral-600 dark:text-neutral-400">By {article.author}</div>
            )}
          </div>
        </div>

        <h1 className="mb-4 text-4xl font-semibold leading-tight text-neutral-900 dark:text-white">
          {article.title}
        </h1>

        {article.summary && (
          <p className="mb-6 text-lg text-neutral-700 dark:text-neutral-300">{article.summary}</p>
        )}

        {article.tags && article.tags.length > 0 && (
          <div className="mb-8 flex flex-wrap gap-2">
            {article.tags.map((tag) => (
              <span
                key={tag}
                className={clsx("tag", `tag-${tag.toLowerCase().replace(/\s+/g, "-")}`)}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children, ...props }) => (
              <h2 className="text-2xl font-semibold text-neutral-900 dark:text-white" {...props}>
                {children}
              </h2>
            ),
            h2: ({ children, ...props }) => (
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white" {...props}>
                {children}
              </h3>
            ),
            p: ({ children, ...props }) => (
              <p className="mb-4 text-neutral-700 dark:text-neutral-300" {...props}>
                {children}
              </p>
            ),
            ul: ({ children, ...props }) => (
              <ul className="mb-4 list-disc pl-6 text-neutral-700 dark:text-neutral-300" {...props}>
                {children}
              </ul>
            ),
            ol: ({ children, ...props }) => (
              <ol className="mb-4 list-decimal pl-6 text-neutral-700 dark:text-neutral-300" {...props}>
                {children}
              </ol>
            ),
            li: ({ children, ...props }) => (
              <li className="mb-2" {...props}>
                {children}
              </li>
            ),
            blockquote: ({ children, ...props }) => (
              <blockquote
                className="border-l-4 border-[#ff5f42] pl-4 italic text-neutral-700 dark:text-neutral-300"
                {...props}
              >
                {children}
              </blockquote>
            ),
            a: ({ children, ...props }) => (
              <a
                className="text-[#ff5f42] hover:underline"
                target="_blank"
                rel="noopener noreferrer"
                {...props}
              >
                {children}
              </a>
            ),
          }}
        >
          {article.content}
        </ReactMarkdown>
      </article>
    </div>
  );
}
