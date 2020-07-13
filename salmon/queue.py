"""
Simpler queue management than the regular mailbox.Maildir stuff.  You
do get a lot more features from the Python library, so if you need
to do some serious surgery go use that.  This works as a good
API for the 90% case of "put mail in, get mail out" queues.
"""
import contextlib
import errno
import fcntl
import hashlib
import logging
import mailbox
import os
import socket
import time
import json

from salmon import mail

# we calculate this once, since the hostname shouldn't change for every
# email we put in a queue
HASHED_HOSTNAME = hashlib.md5(socket.gethostname().encode("utf-8")).hexdigest()


class SafeMaildir(mailbox.Maildir):
    def _create_tmp(self):
        now = time.time()
        uniq = "%s.M%sP%sQ%s.%s" % (int(now), int(now % 1 * 1e6), os.getpid(),
                                    mailbox.Maildir._count, HASHED_HOSTNAME)
        path = os.path.join(self._path, 'tmp', uniq)
        try:
            os.stat(path)
        except OSError as e:
            if e.errno == errno.ENOENT:
                mailbox.Maildir._count += 1
                try:
                    return mailbox._create_carefully(path)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
            else:
                raise

        # Fall through to here if stat succeeded or open raised EEXIST.
        raise mailbox.ExternalClashError('Name clash prevented file creation: %s' % path)


class Queue:
    """
    Provides a simplified API for dealing with 'queues' in Salmon.
    It currently just supports Maildir queues since those are the
    most robust, but could implement others later.
    """

    def __init__(self, queue_dir, safe=False, pop_limit=0, oversize_dir=None):
        """
        This gives the Maildir queue directory to use, and whether you want
        this Queue to use the SafeMaildir variant which hashes the hostname
        so you can expose it publicly.

        The pop_limit and oversize_queue both set a upper limit on the mail
        you pop out of the queue.  The size is checked before any Salmon
        processing is done and is based on the size of the file on disk.  The
        purpose is to prevent people from sending 10MB attachments.  If a
        message is over the pop_limit then it is placed into the
        oversize_dir (which should be a Maildir).

        The oversize protection only works on pop messages off, not
        putting them in, get, or any other call.  If you use get you can
        use self.oversize to also check if it's oversize manually.
        """
        self.dir = queue_dir

        if safe:
            self.mbox = SafeMaildir(queue_dir)
        else:
            self.mbox = mailbox.Maildir(queue_dir)

        self.pop_limit = pop_limit

        if oversize_dir:
            if not os.path.exists(oversize_dir):
                mailbox.Maildir(oversize_dir)

            self.oversize_dir = os.path.join(oversize_dir, "new")

            try:
                os.mkdir(self.oversize_dir)
            except FileExistsError:
                pass
        else:
            self.oversize_dir = None

    def push(self, message):
        """
        Pushes the message onto the queue.  Remember the order is probably
        not maintained.  It returns the key that gets created.
        """
        if not isinstance(message, (str, bytes)):
            # bytes is ok, but anything else needs to be turned into str
            message = str(message)
        return self.mbox.add(message)

    def _move_oversize(self, key, name):
        if self.oversize_dir:
            logging.info("Message key %s over size limit %d, moving to %s.",
                         key, self.pop_limit, self.oversize_dir)
            os.rename(name, os.path.join(self.oversize_dir, key))
        else:
            logging.info("Message key %s over size limit %d, DELETING (set oversize_dir).",
                         key, self.pop_limit)
            os.unlink(name)

    def pop(self):
        """
        Pops a message off the queue, order is not really maintained
        like a stack.

        It returns a (key, message) tuple for that item.
        """
        for key in self.mbox.iterkeys():
            over, over_name = self.oversize(key)

            if over:
                self._move_oversize(key, over_name)
            else:
                msg = self.get(key)
                self.remove(key)
                return key, msg

        return None, None

    def get(self, key):
        """
        Get the specific message referenced by the key.  The message is NOT
        removed from the queue.
        """
        msg_file = self.mbox.get_file(key)

        if not msg_file:
            return None

        msg_data = msg_file.read()

        try:
            return mail.MailRequest(self.dir, None, None, msg_data)
        except Exception as exc:
            logging.exception("Failed to decode message: %s; msg_data: %r", exc, msg_data)
            return None

    def remove(self, key):
        """Removes key the queue."""
        self.mbox.remove(key)

    def __len__(self):
        """Returns the number of messages in the queue."""
        return len(self.mbox)

    # synonym of __len__ for backwards compatibility
    count = __len__

    def clear(self):
        """
        Clears out the contents of the entire queue.
        """
        self.mbox.clear()

    def keys(self):
        """
        Returns the keys in the queue.
        """
        return self.mbox.keys()

    def oversize(self, key):
        if self.pop_limit:
            file_name = os.path.join(self.dir, "new", key)
            return os.path.getsize(file_name) > self.pop_limit, file_name
        else:
            return False, None


class Metadata:
    def __init__(self, path):
        self.path = os.path.join(path, "metadata")
        self.meta_file = None
        try:
            os.mkdir(self.path)
        except FileExistsError:
            pass

    def get(self):
        return json.load(self.meta_file)

    def set(self, key, data):
        json.dump(self.meta_file, data)

    def remove(self):
        os.unlink(self.meta_file)

    def clear(self):
        raise NotImplementedError

    @contextlib.contextmanager
    def lock(self, key, mode="r"):
        i = 0
        try:
            self.meta_file = open(os.path.join(self.path, key), mode)
        except FileNotFoundError:
            pass
        else:
            while True:
                # try for a lock using exponential backoff
                try:
                    fcntl.flock(self.meta_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    if i > 5:
                        # 2**5 is 30 seconds which is far too long
                        raise
                    time.sleep(2**i)
                    i += 1
                else:
                    break

        try:
            yield self
        finally:
            if self.meta_file is not None:
                fcntl.flock(self.meta_file, fcntl.LOCK_UN)
                self.meta_file.close()
                self.meta_file = None


class QueueWithMetadata(Queue):
    """Just like Queue, except it stores envelope data"""
    def push(self, message, Peer, From, To):
        if not isinstance(To, list):
            To = [To]
        key = super().push(message)
        with Metadata(self.dir).lock(key, "w") as metadata:
            metadata.set(key, {"Peer": Peer, "From": From, "To": To})
        return key

    def get(self, key):
        with Metadata(self.dir).lock(key) as metadata:
            msg = super().get(key)
            data = metadata.get(key)
            # move data from metadata to msg obj
            for k, v in data.items():
                setattr(msg, k, v)
            data["To"].remove(msg.To)
            metadata.set(data)
        return msg

    def remove(self, key):
        with Metadata(self.dir).lock(key) as metadata:
            data = metadata.get(key)
            # if there's still a To to be processed, leave the message on disk
            if not data.get("To"):
                super().remove(key)
                metadata.remove()

    def clear(self):
        Metadata(self.dir).clear()
        super().clear()
