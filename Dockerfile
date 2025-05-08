# Utiliser une image de base légère compatible avec votre architecture
FROM --platform=linux/arm64 debian:bullseye-slim

# Éviter les interactions lors de l'installation des paquets
ENV DEBIAN_FRONTEND=noninteractive

# Mettre à jour le système et installer les dépendances nécessaires
RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    git \
    g++ \
    cmake \
    libbluetooth-dev \
    pkg-config \
    libglib2.0-dev \
    python3-dev \
    libcap2-bin \
    python3-tk \
    tk-dev \
    && rm -rf /var/lib/apt/lists/*

# Télécharger et installer Python 3.12.4
RUN wget https://www.python.org/ftp/python/3.12.4/Python-3.12.4.tgz && \
    tar -xf Python-3.12.4.tgz && \
    cd Python-3.12.4 && \
    ./configure --enable-optimizations --with-tcltk-includes='-I/usr/include/tcl8.6' --with-tcltk-libs='/usr/lib/x86_64-linux-gnu/libtcl8.6.so /usr/lib/x86_64-linux-gnu/libtk8.6.so' && \
    make -j $(nproc) && \
    make altinstall && \
    cd .. && rm -rf Python-3.12.4 Python-3.12.4.tgz

# Définir Python 3.12 comme version par défaut
RUN update-alternatives --install /usr/bin/python python /usr/local/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/local/bin/pip3.12 1

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers du projet
COPY requirements.txt .

# Créer et activer l'environnement virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installer les dépendances du projet et Streamlit dans l'environnement virtuel
RUN pip install --no-cache-dir -r requirements.txt streamlit

RUN pip install pyserial && \
    pip uninstall -y serial && \
    pip uninstall -y pyserial && \
    pip install pyserial && \
    pip install debugpy


# Ajouter les permissions nécessaires pour bluepy
RUN setcap 'cap_net_raw,cap_net_admin+eip' /usr/local/bin/python3.12

# Exposer le port utilisé par Streamlit (par défaut 8501)
EXPOSE 8501

# Droit d'accès
RUN chmod -R 755 /opt/venv

# Commande pour exécuter l'application Streamlit dans l'environnement virtuel
CMD ["/opt/venv/bin/python", "-m", "streamlit", "run", "src/main.py", "--server.address", "0.0.0.0"]