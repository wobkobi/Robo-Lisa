import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.tree import DecisionTreeClassifier
from imblearn.over_sampling import SMOTE
import logging

logger = logging.getLogger("LisaBotLogger")


def retrain_classifier(df):
    # Retrain the classifier based on the training data.
    logger.info("Starting classifier retraining.")

    X = df["author_and_message"]
    y = df["encoded"].tolist()

    logger.debug("Performing Count Vectorization.")
    vectorizer = CountVectorizer()
    X_counts = vectorizer.fit_transform(X)

    # TFIDF Convert
    logger.debug("Applying TFIDF transformation.")
    tfidf_transformer = TfidfTransformer()
    X_tfidf = tfidf_transformer.fit_transform(X_counts)

    logger.debug("Applying SMOTE for class imbalance.")
    smote = SMOTE(random_state=42, k_neighbors=4)

    X_train, y_train = smote.fit_resample(X_tfidf, y)

    logger.debug("Training Decision Tree Classifier.")
    dt_classifier = DecisionTreeClassifier(
        class_weight="balanced", splitter="random", max_features="sqrt"
    )
    dt_classifier.fit(X_train, y_train)

    logger.info("Classifier retraining completed.")
    return vectorizer, tfidf_transformer, dt_classifier


def update_encoder(df):
    # Encode the emoji column to numeric values.
    logger.info("Updating encoder for emoji column.")

    df["encoded"] = pd.factorize(df["reply_emojis"])[0]
    emojis = pd.factorize(df["reply_emojis"])[1]

    # creating a function to get the emoji back from the numbers.
    encoded_to_string = {i: string for i, string in enumerate(emojis)}

    logger.debug(f"Encoded-to-string mapping created: {encoded_to_string}")
    return encoded_to_string


def filter_df(df):
    # Filter out rows where the emoji reaction appears fewer than 5 times.
    logger.info("Filtering training data based on emoji frequency.")

    df["author_and_message"] = df["author"] + " " + df["original_message"]

    # Count occurrences of each emoji
    emoji_counts = df["reply_emojis"].value_counts()

    # Filter to keep only rows where the emoji reaction count is 5 or more
    filtered_df = df[df["reply_emojis"].map(emoji_counts) >= 5]

    logger.debug(f"Filtered data size: {len(filtered_df)} rows remaining.")
    return filtered_df


def retrain_bot():
    # Retrain the bot's components using the CSV file.
    logger.info("Starting bot retraining process.")

    try:
        df = pd.read_csv("training.csv")
        logger.debug(f"Loaded training data with {len(df)} rows.")
    except FileNotFoundError:
        logger.error("Training CSV file not found. Skipping retraining.")
        return None, None, None, None

    # Ensure there is enough data for retraining
    if df.empty:
        logger.warning("Training data is empty, skipping retraining.")
        return None, None, None, None

    df = filter_df(df)

    # Ensure filtered data is not empty
    if df.empty:
        logger.warning("Filtered training data is empty, skipping retraining.")
        return None, None, None, None

    encoded_to_string = update_encoder(df)
    vectorizer, tfidf_transformer, classifier = retrain_classifier(df)

    logger.info("Bot retraining completed successfully.")
    return vectorizer, tfidf_transformer, classifier, encoded_to_string
