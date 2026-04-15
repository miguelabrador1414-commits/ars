"""
Recovery Logger - Sistema de logs para sesiones de recuperación

Registra:
- Sesiones de recovery
- Comandos ejecutados
- Errores y soluciones
- Estadísticas
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RecoverySession:
    """Sesión de recuperación"""
    id: int
    timestamp: str
    device_soc: str
    device_state: str
    firmware_used: str
    method: str
    status: str  # "success", "failed", "partial"
    duration_seconds: int
    error_message: str
    bootlog_path: str
    notes: str


@dataclass
class CommandLog:
    """Log de comando"""
    session_id: int
    timestamp: str
    command: str
    output: str
    return_code: int


class RecoveryLogger:
    """
    Sistema de logging para recovery sessions.
    Usa SQLite para persistencia.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path.home() / ".local" / "share" / "ars" / "recovery_log.db"
            
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        
    def _init_database(self):
        """Inicializa la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_soc TEXT,
                device_state TEXT,
                firmware_used TEXT,
                method TEXT,
                status TEXT,
                duration_seconds INTEGER,
                error_message TEXT,
                bootlog_path TEXT,
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TEXT NOT NULL,
                command TEXT NOT NULL,
                output TEXT,
                return_code INTEGER,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TEXT NOT NULL,
                error_type TEXT,
                error_message TEXT,
                solution TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def start_session(self,
                      device_soc: str = "",
                      device_state: str = "",
                      firmware_used: str = "",
                      method: str = "") -> int:
        """
        Inicia una nueva sesión de recovery.
        
        Returns:
            ID de la sesión
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions 
            (timestamp, device_soc, device_state, firmware_used, method, status, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), device_soc, device_state, 
              firmware_used, method, "in_progress", 0))
            
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Session started: {session_id}")
        return session_id
        
    def end_session(self,
                    session_id: int,
                    status: str,
                    error_message: str = "",
                    notes: str = ""):
        """
        Finaliza una sesión de recovery.
        
        Args:
            session_id: ID de la sesión
            status: "success", "failed", "partial"
            error_message: Mensaje de error si falló
            notes: Notas adicionales
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT timestamp FROM sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        
        if row:
            start_time = datetime.fromisoformat(row[0])
            duration = int((datetime.now() - start_time).total_seconds())
        else:
            duration = 0
            
        cursor.execute('''
            UPDATE sessions
            SET status = ?, error_message = ?, notes = ?, duration_seconds = ?
            WHERE id = ?
        ''', (status, error_message, notes, duration, session_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Session {session_id} ended: {status}")
        
    def log_command(self,
                    session_id: int,
                    command: str,
                    output: str = "",
                    return_code: int = 0):
        """Registra un comando ejecutado"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO commands (session_id, timestamp, command, output, return_code)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, datetime.now().isoformat(), command, output, return_code))
        
        conn.commit()
        conn.close()
        
    def log_error(self,
                  session_id: int,
                  error_type: str,
                  error_message: str,
                  solution: str = ""):
        """Registra un error"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO errors (session_id, timestamp, error_type, error_message, solution)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, datetime.now().isoformat(), error_type, 
              error_message, solution))
        
        conn.commit()
        conn.close()
        
    def save_bootlog(self,
                     session_id: int,
                     bootlog: str) -> str:
        """
        Guarda bootlog a archivo.
        
        Returns:
            Ruta al archivo guardado
        """
        log_dir = Path.home() / ".local" / "share" / "ars" / "bootlogs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"bootlog_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = log_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(f"Session: {session_id}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            f.write(bootlog)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET bootlog_path = ? WHERE id = ?',
                      (str(filepath), session_id))
        conn.commit()
        conn.close()
        
        return str(filepath)
        
    def get_session(self, session_id: int) -> Optional[RecoverySession]:
        """Obtiene una sesión por ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        
        if row:
            session = RecoverySession(**dict(row))
        else:
            session = None
            
        conn.close()
        return session
        
    def get_all_sessions(self, 
                         limit: int = 50,
                         status_filter: str = None) -> List[RecoverySession]:
        """Obtiene todas las sesiones"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM sessions'
        params = []
        
        if status_filter:
            query += ' WHERE status = ?'
            params.append(status_filter)
            
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        sessions = [RecoverySession(**dict(row)) for row in rows]
        conn.close()
        
        return sessions
        
    def get_session_commands(self, session_id: int) -> List[CommandLog]:
        """Obtiene comandos de una sesión"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM commands WHERE session_id = ? ORDER BY timestamp',
                      (session_id,))
        rows = cursor.fetchall()
        
        commands = [CommandLog(session_id=r['session_id'],
                             timestamp=r['timestamp'],
                             command=r['command'],
                             output=r['output'],
                             return_code=r['return_code']) 
                   for r in rows]
        conn.close()
        
        return commands
        
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas de todas las sesiones"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sessions WHERE status = "success"')
        successful = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sessions WHERE status = "failed"')
        failed = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(duration_seconds) FROM sessions WHERE duration_seconds > 0')
        avg_duration = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT device_soc, COUNT(*) as count 
            FROM sessions 
            WHERE device_soc != ''
            GROUP BY device_soc 
            ORDER BY count DESC
        ''')
        by_soc = [{'soc': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_sessions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'average_duration_seconds': int(avg_duration),
            'by_soc': by_soc
        }
        
    def export_session(self, session_id: int) -> Dict:
        """Exporta una sesión completa como dict"""
        session = self.get_session(session_id)
        if not session:
            return {}
            
        commands = self.get_session_commands(session_id)
        
        return {
            'session': asdict(session),
            'commands': [asdict(cmd) for cmd in commands]
        }
        
    def clear_old_sessions(self, days: int = 90):
        """Elimina sesiones antiguas"""
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM commands WHERE session_id IN (SELECT id FROM sessions WHERE timestamp < ?)',
                      (cutoff,))
        cursor.execute('DELETE FROM errors WHERE session_id IN (SELECT id FROM sessions WHERE timestamp < ?)',
                      (cutoff,))
        cursor.execute('DELETE FROM sessions WHERE timestamp < ?', (cutoff,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleared {deleted} old sessions")
        return deleted


class RecoveryReport:
    """Generador de reportes de recovery"""
    
    def __init__(self, logger: RecoveryLogger):
        self.logger = logger
        
    def generate_report(self, session_id: int) -> str:
        """Genera un reporte textual de la sesión"""
        session = self.logger.get_session(session_id)
        if not session:
            return "Sesión no encontrada"
            
        commands = self.logger.get_session_commands(session_id)
        stats = self.logger.get_statistics()
        
        report = f"""
{'='*60}
REPORTE DE RECUPERACIÓN - ARS
{'='*60}

📋 INFORMACIÓN DE SESIÓN
─────────────────────────────
ID: {session.id}
Fecha: {session.timestamp}
SOC: {session.device_soc}
Estado: {session.device_state}
Método: {session.method}
Estado: {session.status.upper()}

📦 FIRMWARE
─────────────────────────────
Usado: {session.firmware_used or 'N/A'}

⏱️ DURACIÓN
─────────────────────────────
{self._format_duration(session.duration_seconds)}

{'⚠️ ERROR' if session.error_message else '✓ ÉXITO'}
─────────────────────────────
{session.error_message or 'Sin errores'}

📝 NOTAS
─────────────────────────────
{session.notes or 'Sin notas'}

📊 HISTORIAL
─────────────────────────────
Total sesiones: {stats['total_sessions']}
Éxitos: {stats['successful']}
Fallidos: {stats['failed']}
Tasa de éxito: {stats['success_rate']:.1f}%

{'='*60}
"""
        return report
        
    def _format_duration(self, seconds: int) -> str:
        """Formatea duración"""
        if seconds < 60:
            return f"{seconds} segundos"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins} min {secs} seg"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours} hr {mins} min"
            
    def export_html(self, session_id: int, output_path: str):
        """Exporta reporte como HTML"""
        session = self.logger.get_session(session_id)
        if not session:
            return False
            
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ARS Recovery Report - Session {session_id}</title>
    <style>
        body {{ font-family: monospace; padding: 20px; }}
        .header {{ background: #2196F3; color: white; padding: 20px; }}
        .section {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; }}
        .success {{ color: green; }}
        .failed {{ color: red; }}
        .commands {{ background: #f5f5f5; padding: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ARS Recovery Report</h1>
        <p>Session #{session.id}</p>
    </div>
    
    <div class="section">
        <h2>Session Info</h2>
        <p><strong>Date:</strong> {session.timestamp}</p>
        <p><strong>SOC:</strong> {session.device_soc}</p>
        <p><strong>Status:</strong> <span class="{session.status}">{session.status.upper()}</span></p>
    </div>
    
    <div class="section">
        <h2>Result</h2>
        <p>{session.error_message or 'Recovery completed successfully'}</p>
    </div>
</body>
</html>"""
        
        with open(output_path, 'w') as f:
            f.write(html)
            
        return True
