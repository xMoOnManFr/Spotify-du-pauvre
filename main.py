import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSlider, QFrame, QLineEdit,
    QMessageBox, QFileDialog  # NOUVEAU: Pour la sélection de dossier
)
from PyQt6.QtCore import Qt, QUrl, QTime
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import yt_dlp

# --- Configurations Globales ---
PRIMARY_COLOR = "#1DB954"
BACKGROUND_COLOR = "#121212"
FOREGROUND_COLOR = "#FFFFFF"
MILD_GRAY = "#282828"

# Chemin de votre dossier audio (Désormais défini dynamiquement)
# FOLDER_PATH = r"C:\Users\xMoOnManFr\Documents\Audio files python project" # Remplacé

# Fichier de stockage des playlists
PLAYLIST_FILE = "playlists.json"
# Fichier de configuration pour stocker le chemin du dossier audio
CONFIG_FILE = "config.json"
DEFAULT_FOLDER_NAME = "Audio files python project"  # Nom du dossier par défaut à créer


class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify du pauvre (PyQt)")
        self.setGeometry(100, 100, 400, 850)

        # --- NOUVEAU : Assurer que le dossier audio existe ---
        self.audio_folder_path = self.ensure_audio_folder()
        if not self.audio_folder_path:
            # Si l'utilisateur annule le dialogue, on quitte l'application
            sys.exit(0)

        # --- Variables d'état des Playlists ---
        self.all_files_in_folder = [f for f in os.listdir(self.audio_folder_path) if f.endswith(".mp3")]

        self.playlists = self.load_playlists()

        if not self.playlists:
            self.playlists = {"Toutes les pistes": self.all_files_in_folder.copy()}

        self.current_playlist_name = list(self.playlists.keys())[0]
        self.current_playlist_files = self.playlists[self.current_playlist_name]
        self.current_track_index = -1
        self.is_user_seeking = False

        # --- 1. Initialisation des composants PyQt Multimédia ---
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # Connexions
        self.media_player.positionChanged.connect(self.update_progress)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)
        self.media_player.playbackStateChanged.connect(self.update_play_pause_button)
        self.audio_output.volumeChanged.connect(self.on_volume_changed)

        self.setup_ui()
        self.set_style()
        self.load_initial_playlist()

        self.update_available_tracks_combo()

    def closeEvent(self, event):
        """Surcharge l'événement de fermeture pour sauvegarder les playlists."""
        self.save_playlists()
        event.accept()

    # --- NOUVELLE FONCTION DE GESTION DE DOSSIER ---

    def ensure_audio_folder(self):
        """Vérifie si le chemin du dossier audio est stocké ou demande à l'utilisateur de le définir."""
        path = None

        # 1. Tenter de charger le chemin depuis le fichier de configuration
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    path = config.get("audio_folder_path")
                    if path and not os.path.isdir(path):
                        # Le chemin stocké n'est plus valide, on le réinitialise
                        QMessageBox.warning(self, "Chemin Invalide",
                                            f"Le dossier audio stocké ({path}) n'existe plus. Veuillez en sélectionner un nouveau.")
                        path = None
            except:
                path = None  # Fichier corrompu

        # 2. Si le chemin n'est pas défini, demander à l'utilisateur
        if not path:
            QMessageBox.information(self, "Configuration Initiale",
                                    f"Veuillez sélectionner le dossier où seront stockés vos fichiers MP3 et où sera créé le dossier '{DEFAULT_FOLDER_NAME}'.")

            # Ouvrir le dialogue de sélection de dossier
            selected_directory = QFileDialog.getExistingDirectory(
                self,
                "Sélectionner le Dossier Racine pour la Musique",
                os.path.expanduser("~")  # Démarre dans le répertoire utilisateur
            )

            if selected_directory:
                # Créer le sous-dossier dédié
                path = os.path.join(selected_directory, DEFAULT_FOLDER_NAME)
                try:
                    os.makedirs(path, exist_ok=True)
                    self.save_config({"audio_folder_path": path})
                    QMessageBox.information(self, "Dossier Créé",
                                            f"Le dossier audio a été créé avec succès : {path}")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur de Création",
                                         f"Impossible de créer le dossier à : {path}\nErreur: {e}")
                    return None
            else:
                QMessageBox.warning(self, "Annulation", "Configuration annulée. L'application va se fermer.")
                return None

        return path

    def save_config(self, config_data):
        """Sauvegarde les données de configuration, notamment le chemin du dossier audio."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Erreur de Sauvegarde Configuration",
                                 f"Impossible de sauvegarder le fichier de configuration : {e}")

    # --- SETUP UI (inchangé) ---

    def set_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {BACKGROUND_COLOR};
                color: {FOREGROUND_COLOR};
            }}
            QLabel {{
                color: {FOREGROUND_COLOR};
                font-family: Roboto;
            }}
            QPushButton {{
                background-color: {MILD_GRAY};
                color: {FOREGROUND_COLOR};
                border: none;
                padding: 10px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_COLOR};
                color: {BACKGROUND_COLOR};
            }}
            QComboBox, QLineEdit {{
                background-color: {MILD_GRAY};
                color: {FOREGROUND_COLOR};
                border: 1px solid {PRIMARY_COLOR};
                padding: 5px;
                border-radius: 3px;
            }}
            #PlayPauseButton {{ 
                font-weight: bold;
            }}
            #PlayPauseButton[status="Play"] {{
                background-color: {PRIMARY_COLOR};
                color: {BACKGROUND_COLOR};
            }}
            #PlayPauseButton[status="Pause"] {{
                background-color: #FF5733; 
                color: {FOREGROUND_COLOR};
            }}
            QFrame#EditFrame {{
                border: 1px dashed {PRIMARY_COLOR};
                padding: 10px;
                margin-top: 20px;
                margin-bottom: 20px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {MILD_GRAY};
                height: 8px;
                background: {MILD_GRAY};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {PRIMARY_COLOR};
                border: 1px solid {PRIMARY_COLOR};
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {PRIMARY_COLOR};
                border-radius: 4px;
            }}
        """)

    def setup_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        self.setCentralWidget(central_widget)

        self.status_label = QLabel("Choisissez une playlist et une piste.")
        self.status_label.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {PRIMARY_COLOR};")
        main_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        playlist_layout = QHBoxLayout()
        playlist_layout.addWidget(QLabel("Playlist active:"))
        self.playlist_combo = QComboBox()
        self.playlist_combo.addItems(list(self.playlists.keys()))
        self.playlist_combo.currentTextChanged.connect(self.change_playlist)
        playlist_layout.addWidget(self.playlist_combo)
        main_layout.addLayout(playlist_layout)

        files_layout = QHBoxLayout()
        files_layout.addWidget(QLabel("Piste à jouer:"))
        self.combo = QComboBox()
        self.combo.currentTextChanged.connect(self.select_track_from_list)
        files_layout.addWidget(self.combo)
        main_layout.addLayout(files_layout)

        edit_frame = QFrame()
        edit_frame.setObjectName("EditFrame")
        edit_layout = QVBoxLayout(edit_frame)
        edit_layout.setSpacing(10)

        new_playlist_layout = QHBoxLayout()
        self.new_playlist_name_input = QLineEdit()
        self.new_playlist_name_input.setPlaceholderText("Nom de la nouvelle playlist")
        self.create_playlist_btn = QPushButton("Créer Playlist")
        self.create_playlist_btn.clicked.connect(self.create_new_playlist)

        new_playlist_layout.addWidget(self.new_playlist_name_input)
        new_playlist_layout.addWidget(self.create_playlist_btn)
        edit_layout.addLayout(new_playlist_layout)

        add_track_layout = QHBoxLayout()
        add_track_label = QLabel("Piste à ajouter :")
        self.all_tracks_combo = QComboBox()
        self.add_track_btn = QPushButton("Ajouter à la Playlist active")
        self.add_track_btn.clicked.connect(self.add_track_to_current_playlist)

        add_track_layout.addWidget(add_track_label)
        add_track_layout.addWidget(self.all_tracks_combo)
        add_track_layout.addWidget(self.add_track_btn)
        edit_layout.addLayout(add_track_layout)

        download_group = QFrame()
        download_group.setStyleSheet("background-color: #333333; padding: 10px; border-radius: 5px;")
        download_layout = QVBoxLayout(download_group)
        download_layout.addWidget(QLabel("Téléchargement YouTube (MP3):"))

        download_input_layout = QHBoxLayout()
        self.youtube_url_input = QLineEdit()
        self.youtube_url_input.setPlaceholderText("Coller l'URL YouTube ici...")
        self.download_btn = QPushButton("⇩ Télécharger MP3")
        self.download_btn.clicked.connect(self.download_youtube_mp3)

        download_input_layout.addWidget(self.youtube_url_input)
        download_input_layout.addWidget(self.download_btn)

        download_layout.addLayout(download_input_layout)
        edit_layout.addWidget(download_group)

        main_layout.addWidget(edit_frame)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderPressed.connect(self.start_seek)
        self.progress_slider.sliderReleased.connect(self.end_seek)
        self.progress_slider.sliderMoved.connect(self.seek_preview)
        main_layout.addWidget(self.progress_slider)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        main_layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignCenter)

        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)

        self.prev_btn = QPushButton("<< Préc.")
        self.play_pause_btn = QPushButton("▶ PLAY")
        self.play_pause_btn.setObjectName("PlayPauseButton")
        self.next_btn = QPushButton("Suiv. >>")

        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.next_btn)

        util_frame = QFrame()
        util_layout = QHBoxLayout(util_frame)
        self.stop_btn = QPushButton("■ STOP")

        util_layout.addWidget(self.stop_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(controls_frame)
        main_layout.addWidget(util_frame)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.set_volume)

        volume_label = QLabel("Volume:")
        volume_container = QHBoxLayout()
        volume_container.addWidget(volume_label)
        volume_container.addWidget(self.volume_slider)
        main_layout.addLayout(volume_container)

        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.prev_btn.clicked.connect(self.prev_track)
        self.next_btn.clicked.connect(self.next_track)
        self.stop_btn.clicked.connect(self.stop_track)

    # --- LOGIQUE DE FILTRAGE DES PISTES DISPONIBLES (inchangée) ---

    def update_available_tracks_combo(self):
        """Met à jour la liste déroulante des pistes disponibles pour l'ajout."""
        self.all_tracks_combo.blockSignals(True)
        self.all_tracks_combo.clear()

        is_modifiable = self.current_playlist_name != "Toutes les pistes"

        if is_modifiable:
            tracks_in_active_playlist = set(self.current_playlist_files)
            available_tracks = [
                track for track in self.all_files_in_folder
                if track not in tracks_in_active_playlist
            ]
        else:
            available_tracks = []

        if available_tracks:
            self.all_tracks_combo.addItems(available_tracks)

        self.add_track_btn.setEnabled(len(available_tracks) > 0 and is_modifiable)

        self.all_tracks_combo.blockSignals(False)

    # --- FONCTION DE TÉLÉCHARGEMENT YOUTUBE (Mise à jour du chemin) ---

    def download_youtube_mp3(self):
        """Télécharge la vidéo YouTube comme fichier MP3 dans le dossier défini."""
        url = self.youtube_url_input.text().strip()

        if not url:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL YouTube.")
            return

        self.status_label.setText("Téléchargement en cours... Veuillez patienter.")
        self.download_btn.setEnabled(False)

        ydl_opts = {
            'format': 'bestaudio/best',
            # ATTENTION : Utilisation de self.audio_folder_path
            'outtmpl': os.path.join(self.audio_folder_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'ignoreerrors': True,
            'noplaylist': True,
            'ffmpeg_location': 'ffmpeg',
            'progress_hooks': [self.download_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filename_base = ydl.prepare_filename(info).rsplit('.', 1)[0]
                final_filename = os.path.basename(filename_base + '.mp3')

                ydl.download([url])

            self.status_label.setText(f"Téléchargement réussi : {final_filename}")

            self.refresh_all_file_lists(final_filename)
            self.youtube_url_input.clear()

        except yt_dlp.utils.DownloadError as e:
            QMessageBox.critical(self, "Erreur de Téléchargement", f"Erreur yt-dlp : {e}")
            self.status_label.setText("Échec du téléchargement.")
        except FileNotFoundError:
            QMessageBox.critical(self, "Erreur FFmpeg",
                                 "FFmpeg n'est pas trouvé. Veuillez l'installer et vous assurer qu'il est dans votre PATH.")
            self.status_label.setText("Échec : FFmpeg manquant.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur inattendue est survenue : {e}")
            self.status_label.setText("Échec du téléchargement.")
        finally:
            self.download_btn.setEnabled(True)

    def download_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', 'N/A')
            self.status_label.setText(f"Téléchargement en cours : {p}...")
        elif d['status'] == 'finished':
            self.status_label.setText("Téléchargement terminé, conversion en MP3...")

    def refresh_all_file_lists(self, new_track_name):
        if new_track_name not in self.all_files_in_folder:
            self.all_files_in_folder.append(new_track_name)

        self.playlists["Toutes les pistes"] = self.all_files_in_folder.copy()

        self.save_playlists()

        self.update_available_tracks_combo()

        if self.current_playlist_name == "Toutes les pistes":
            self.current_playlist_files = self.playlists["Toutes les pistes"]
            self.update_files_combo()
            self.combo.setCurrentText(new_track_name)

    # --- FONCTIONS DE GESTION DE PLAYLIST (Mise à jour) ---

    def save_playlists(self):
        """Sauvegarde les playlists."""
        try:
            with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Erreur de Sauvegarde", f"Impossible de sauvegarder les playlists : {e}")

    def load_playlists(self):
        """Charge les playlists et met à jour 'Toutes les pistes' avec le contenu actuel du dossier."""
        if os.path.exists(PLAYLIST_FILE):
            try:
                with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data["Toutes les pistes"] = self.all_files_in_folder.copy()
                    return data
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Erreur de Fichier",
                                    "Le fichier de playlists est corrompu. Création d'une nouvelle liste.")
                return None
            except Exception as e:
                QMessageBox.critical(self, "Erreur de Chargement", f"Impossible de charger les playlists : {e}")
                return None
        return None

    def create_new_playlist(self):
        name = self.new_playlist_name_input.text().strip()

        if not name or name in self.playlists:
            QMessageBox.warning(self, "Erreur", "Nom invalide ou déjà existant.")
            return

        self.playlists[name] = []
        self.save_playlists()

        self.playlist_combo.addItem(name)
        self.playlist_combo.setCurrentText(name)
        self.new_playlist_name_input.clear()
        self.status_label.setText(f"Playlist '{name}' créée et sélectionnée.")

    def add_track_to_current_playlist(self):
        selected_track = self.all_tracks_combo.currentText()

        if not selected_track:
            QMessageBox.warning(self, "Attention", "Aucune piste disponible à ajouter.")
            return

        if self.current_playlist_name == "Toutes les pistes":
            QMessageBox.warning(self, "Attention", "Vous ne pouvez pas modifier la playlist 'Toutes les pistes'.")
            return

        self.current_playlist_files.append(selected_track)
        self.save_playlists()

        self.update_available_tracks_combo()

        self.update_files_combo()
        self.status_label.setText(f"Piste ajoutée à '{self.current_playlist_name}'.")
        self.combo.setCurrentText(selected_track)

        # --- Fonctions de lecture (Mise à jour du chemin) ---

    def format_time(self, milliseconds):
        time_obj = QTime(0, 0, 0)
        time_obj = time_obj.addMSecs(milliseconds)
        return time_obj.toString("mm:ss")

    def load_initial_playlist(self):
        self.update_files_combo()
        if self.current_playlist_files:
            self.load_track(0)

    def change_playlist(self, playlist_name):
        if self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.media_player.stop()

        self.current_playlist_name = playlist_name
        self.current_playlist_files = self.playlists.get(playlist_name, [])
        self.current_track_index = -1

        self.update_files_combo()
        self.update_available_tracks_combo()

        self.status_label.setText(f"Playlist chargée : {playlist_name}")

    def update_files_combo(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        if self.current_playlist_files:
            self.combo.addItems(self.current_playlist_files)
            if self.current_playlist_files:
                self.combo.setCurrentIndex(0)
        self.combo.blockSignals(False)

    def select_track_from_list(self, track_name):
        if track_name and track_name in self.current_playlist_files:
            index = self.current_playlist_files.index(track_name)
            self.load_track(index)

    def load_track(self, index):
        if not (0 <= index < len(self.current_playlist_files)): return

        self.current_track_index = index
        track_name = self.current_playlist_files[index]
        # ATTENTION : Utilisation de self.audio_folder_path
        path_audiofile = os.path.join(self.audio_folder_path, track_name)

        self.status_label.setText(f"Piste sélectionnée : {track_name}")
        self.combo.setCurrentText(track_name)
        self.media_player.setSource(QUrl.fromLocalFile(path_audiofile))

    def toggle_play_pause(self):
        state = self.media_player.playbackState()

        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.status_label.setText("Pause activée")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.media_player.play()
            self.status_label.setText(f"Lecture reprise : {self.current_playlist_files[self.current_track_index]}")
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            if self.current_track_index == -1 and self.current_playlist_files:
                self.load_track(0)
            elif not self.current_playlist_files:
                self.status_label.setText("Erreur : La playlist est vide. Ajoutez des pistes manuellement.")
                return

            self.media_player.play()
            self.status_label.setText(f"Lecture en cours : {self.current_playlist_files[self.current_track_index]}")

    def update_play_pause_button(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setText("⏸ PAUSE")
            self.play_pause_btn.setProperty("status", "Pause")
        else:
            self.play_pause_btn.setText("▶ PLAY")
            self.play_pause_btn.setProperty("status", "Play")
        self.play_pause_btn.style().polish(self.play_pause_btn)

    def stop_track(self):
        self.media_player.stop()
        self.status_label.setText("Lecture stoppée")

    def next_track(self):
        if not self.current_playlist_files: return
        self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist_files)
        self.load_track(self.current_track_index)
        self.media_player.play()

    def prev_track(self):
        if not self.current_playlist_files: return
        self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist_files)
        self.load_track(self.current_track_index)
        self.media_player.play()

    def set_volume(self, volume):
        self.audio_output.setVolume(volume / 100)

    def on_volume_changed(self, volume):
        pass

    def update_duration(self, duration):
        self.progress_slider.setMaximum(duration)
        self.time_label.setText(f"00:00 / {self.format_time(duration)}")

    def update_progress(self, position):
        if not self.is_user_seeking:
            self.progress_slider.setValue(position)
            self.time_label.setText(f"{self.format_time(position)} / {self.format_time(self.media_player.duration())}")

    def start_seek(self):
        self.is_user_seeking = True

    def seek_preview(self, position):
        duration = self.media_player.duration()
        self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")

    def end_seek(self):
        seek_position = self.progress_slider.value()
        self.media_player.setPosition(seek_position)
        self.is_user_seeking = False

    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print("Piste terminée : passage à la suivante.")
            self.next_track()


if __name__ == "__main__":
    # Si vous utilisez Windows, lancez le script sous 'votre_script.pyw' pour éviter le terminal.
    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()

    sys.exit(app.exec())