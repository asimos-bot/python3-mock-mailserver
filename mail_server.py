import socket
from enum import Enum
from database import Database

class StatusCode(Enum):
    CLOSING=221
    OK=250
    DOMAIN_NOT_AVAILABLE=421 # must close channel
    SYNTAX_ERROR=500
    NOT_IMPLEMENTED=502
    CONNECTION_ESTABLISHED=220

class MailServer:

    def __init__(self, directory, emails, port: int = 6500):

        self.skt = self.create_server(port)

        self.domain = None
        self.sender = None
        self.recipient = None
        self.client_skt = None
        self.client_addr = None
        self.database = Database(directory, emails)

        self.serve_clients()

    def create_server(self, port):

        # create socket with tcp capabitlities (IP and TCP)
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # set additional configuration to the socket. Here we add
        # the capability to reuse the port when the port closes
        # without this we would need to wait for a timeout when the
        # socket closes (sucks for debugging)

        # SOL_SOCKET means the configuration we are setting are
        # protocol independent.
        skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR | socket.SO_REUSEPORT, 1 )

        # bind the socket to a port, so it can listen for connections
        # going for it
        skt.bind(( '', port ))

        # size of unattended connections queue, from this point on the
        # server is working
        skt.listen(5)

        return skt

    def get_client_bytes(self, num_bytes):
        return self.client_skt.recv(num_bytes).decode("ascii")

    def send_client_bytes(self, buf):

        buf = str(buf)
        # check for no newline
        if( buf[-1] != "\n" ):
            buf = buf + "\r\n"

        return self.client_skt.sendall( buf.encode("ascii") )

    def is_line_finished(self):

        first_byte = self.get_client_bytes(1)

        if( first_byte == "\n"):
            return True
        elif( first_byte == "\r" ):
            return "\n" == self.get_client_bytes(1)
        else:
            return False

    # return line (without newline) and status code
    def get_line(self, max_bytes=4096):

        buf = self.get_client_bytes(1)
        if( buf[-1] not in ['\r', '\n'] ):
            while( buf[-1] not in ['\r', '\n'] ):
                if( len(buf) < max_bytes):
                    buf += self.get_client_bytes(1)
                else:
                    return buf, StatusCode.SYNTAX_ERROR

        # make sure to read last '\n' so we won't read it later
        if( buf[-1] == "\r" and self.get_client_bytes(1) == "\n"):
            return buf[:-1], StatusCode.OK
        elif( buf[-1] == "\n" ):
            return buf[:-1], StatusCode.OK
        else:
            # in this case we got and '\r' NOT followed by and '\n'
            return buf, StatusCode.SYNTAX_ERROR

    def get_new_client(self):
        (self.client_skt, self.client_addr) = self.skt.accept()
        if( self.client_skt ):
            # connection established
            self.send_client_bytes(StatusCode.CONNECTION_ESTABLISHED.value)

    def serve_clients(self):

        # accept new client. Since we didn't specify otherwise,
        # the program will hang here until somebody connects
        self.domain = self.recipient = self.sender = None
        self.get_new_client()

        # clients can disconnect, but the server never dies
        while(True):

            # get their commands and respond to them...

            # * pegar username com HELO
            # * pegar recipiente/destinatario com RCPT/MAIL
            # * enviar emails para database com DATA
            # * responder OK para NOOP
            # * abortar conexão imediatamente com RSET
            # * fechar conexao com QUIT (mandar OK antes)

            # wait for another client if any error occur
            try:
                # 4 first bytes tell us the command given
                command = self.get_client_bytes(4).upper() # NOTE: commands are case insensitive

                # read until the end of the line
                line, status = self.get_line()

                if( status == StatusCode.SYNTAX_ERROR ):
                    self.syntax_error()

                # must be the first command in a session
                if( command == "HELO" ):
                    self.helo(line)
                elif( command == "MAIL"):
                    self.mail(line)
                elif( command == "RCPT" ):
                    self.rcpt(line)
                elif( command == "DATA" ):
                    self.data()
                elif( command == "RSET" ):
                    self.rset()
                elif( command == "NOOP" ):
                    self.noop()
                elif( command == "QUIT" ):
                    self.quit()
                elif( command in ["SEND", "SOML", "SAML", "VRFY", "EXPN", "HELP", "TURN"] ):
                    self.send_client_bytes(StatusCode.NOT_IMPLEMENTED.value)
                else:
                    self.syntax_error()
            except:
                self.get_new_client()

    def helo(self, line):
        self.send_client_bytes(StatusCode.NOT_IMPLEMENTED.value)
    def mail(self, line):
        self.send_client_bytes(StatusCode.NOT_IMPLEMENTED.value)
    def rcpt(self, line):
        self.send_client_bytes(StatusCode.NOT_IMPLEMENTED.value)
    def data(self):
        self.send_client_bytes(StatusCode.NOT_IMPLEMENTED.value)
    def rset(self):
        # any info saved about the current email transaction must be discarted.
        # the connection is not finished tough, so don't throw client_skt and
        # client_addr out
        # also, we keep 'self.domain', since this is about the user, not the
        # mail transaction itself
        self.recipient = None
        self.sender = None

        self.send_client_bytes(StatusCode.OK.value)

    def noop(self):

        # return 250 if domain is available, 421 otherwise
        self.send_client_bytes(StatusCode.OK.value)

    def quit(self):
        # remove current user information
        self.recipient = None
        self.sender = None
        self.domain = None

        # send closing connection signal
        self.send_client_bytes(StatusCode.CLOSING.value)

        # close connection (no more receiving/sending) and close socket's file descriptor
        self.client_skt.close()
        self.client_skt = None
        self.client_addr = None

    def syntax_error(self):
        self.send_client_bytes(StatusCode.SYNTAX_ERROR.value)